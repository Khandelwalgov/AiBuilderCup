"""Source adapters return candidates, never eligibility rules or publication decisions."""

import io
import json
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .network import AcquisitionError, allowed, canonical, challenge
from .schemas import Candidate


def html_links(raw, url, source):
    soup = BeautifulSoup(raw, "html.parser")
    documents, pages = [], []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        target = canonical(urljoin(url, href))
        try:
            allowed(target, source)
        except AcquisitionError:
            continue
        row = a.find_parent("tr")
        # Legacy portals wrap whole layouts in a table row; that is not a document row.
        if row and (row.find("tr") or len(row.select("a[href]")) > 4):
            row = None
        label = a.get_text(" ", strip=True)
        title = row.get_text(" ", strip=True) if row else label
        title = title or a.get("title") or target.rsplit("/", 1)[-1]
        context = title + " " + target
        if re.search(source.exclude_pattern, context):
            continue
        if re.search(source.document_pattern, context):
            relation = (
                "amendment" if re.search(r"(?i)amend|corrigend|addendum", title) else "document"
            )
            related = []
            if row:
                related = [
                    canonical(urljoin(url, link["href"]))
                    for link in row.select("a[href]")
                    if link is not a
                ]
                related = [u for u in related if u != target and u.startswith("https://")]
            documents.append(
                Candidate(
                    url=target,
                    discovery_url=url,
                    title=title[:2000],
                    relation=relation,
                    related_urls=related[:20],
                    association_basis="same_index_row_unverified" if related else None,
                )
            )
        elif re.search(source.page_pattern, target):
            pages.append(target)
    return documents, list(dict.fromkeys(pages))


def feed_links(raw, url, source):
    """JSON {items: [{url,title,...}]} or RSS/Atom. Dates only from explicit ISO fields."""
    if raw.lstrip().startswith((b"{", b"[")):
        try:
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else parsed["items"]
            if not isinstance(rows, list):
                raise ValueError()
            candidates = [Candidate.model_validate({**row, "discovery_url": url}) for row in rows]
        except (ValueError, KeyError, TypeError):
            raise AcquisitionError("invalid_feed") from None
    else:
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise AcquisitionError("unsafe_feed_xml")
        try:
            root = ElementTree.fromstring(raw)
        except ElementTree.ParseError:
            raise AcquisitionError("invalid_feed") from None
        candidates = []
        for item in root.iter():
            if item.tag.split("}")[-1] not in ("item", "entry"):
                continue
            children = {child.tag.split("}")[-1]: child for child in item}
            link, title = children.get("link"), children.get("title")
            if link is not None:
                target = link.get("href") or link.text or ""
                if not target:
                    continue
                publication_date = None
                if "pubDate" in children:
                    try:
                        publication_date = parsedate_to_datetime(children["pubDate"].text).date()
                    except (ValueError, TypeError):
                        pass  # Unparseable source dates stay unknown.
                candidates.append(
                    Candidate(
                        url=canonical(urljoin(url, target)),
                        discovery_url=url,
                        title=title.text if title is not None and title.text else target,
                        publication_date=publication_date,
                    )
                )
    accepted = []
    for candidate in candidates:
        candidate.url = canonical(urljoin(url, candidate.url))
        try:
            allowed(candidate.url, source)
        except AcquisitionError:
            continue
        accepted.append(candidate)
    return accepted, []


def rendered_links(url, source, fetcher):
    """Optional Playwright; every browser request uses the same guarded HTTP transport."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise AcquisitionError("playwright_dependency_unavailable") from None
    failure = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(service_workers="block")
        context.route_web_socket("**/*", lambda ws: ws.close())

        def route_request(route):
            if route.request.method != "GET" or route.request.resource_type in (
                "image",
                "font",
                "media",
                "other",
            ):
                route.abort()
                return
            try:
                p = fetcher.fetch(route.request.url, source)
                route.fulfill(
                    status=p.status,
                    body=p.raw,
                    headers={"content-type": p.headers.get("content-type") or "text/plain"},
                )
            except AcquisitionError as exc:
                failure.append(exc.code)
                route.abort()

        context.route("**/*", route_request)
        try:
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            raw = page.content().encode()
            challenge(raw)
            return html_links(raw, page.url, source)
        except AcquisitionError:
            raise
        except Exception:
            raise AcquisitionError(
                "rendered_listing_unavailable", detail=",".join(failure)
            ) from None
        finally:
            context.close()
            browser.close()


def discover(payload, source, fetcher):
    if source.adapter == "feed":
        return feed_links(payload.raw, payload.final_url, source)
    if source.adapter == "playwright":
        return rendered_links(payload.final_url, source, fetcher)
    if source.adapter == "pdf":
        return [
            Candidate(url=payload.final_url, discovery_url=source.seeds[0], title=source.key)
        ], []
    return html_links(payload.raw, payload.final_url, source)


def validate(raw, media, url):
    """Parse actual PDF bytes; HTML is permitted only for configured document candidates."""
    if raw.startswith(b"%PDF-"):
        try:
            reader = PdfReader(io.BytesIO(raw), strict=True)
            if reader.is_encrypted or len(reader.pages) > 500 or not reader.pages:
                raise ValueError()
            # Resolve every page's content stream without paid OCR/extraction.
            for page in reader.pages:
                page.get_contents()
            return "pdf", {
                "method": "pypdf_structure",
                "pages": len(reader.pages),
                "text_or_eligibility_verified": False,
            }
        except Exception:
            raise AcquisitionError("invalid_pdf") from None
    if "pdf" in media.lower() or re.search(r"(?i)\.pdf(?:$|\?)", url):
        raise AcquisitionError("invalid_pdf")
    if "html" in media.lower():
        challenge(raw)
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup.select("script,style,nav,header,footer"):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        if len(text) < 200:
            raise AcquisitionError("empty_or_javascript_listing")
        return "html", {
            "method": "html_text_presence",
            "text_characters": len(text),
            "text_or_eligibility_verified": False,
        }
    raise AcquisitionError("unsupported_format")
