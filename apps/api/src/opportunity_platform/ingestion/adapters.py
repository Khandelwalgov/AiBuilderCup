"""A small allowlist, not a crawler. No frontend-supplied URL is fetched."""

import io
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

USER_AGENT = "OpportunityIntelligencePrototype/0.2"
MAX_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Adapter:
    key: str
    name: str
    authority: str
    url: str
    context_url: str
    focus: str
    amendment_urls: tuple[str, ...] = ()


ADAPTERS = {
    "depwd-pre-matric": Adapter(
        key="depwd-pre-matric",
        name="DEPwD scholarship guidelines · pre-matric section",
        authority=(
            "Department of Empowerment of Persons with Disabilities, Ministry of Social "
            "Justice and Empowerment"
        ),
        url=(
            "https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2024/09/202409261656732428.pdf"
        ),
        amendment_urls=(
            (
                "https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2025/09/202509111852335844.pdf"
            ),
        ),
        context_url="https://depwd.gov.in/en/scholarship/",
        focus=(
            "Extract ONLY the Pre-Matric Scholarship for Students with Disabilities, "
            "including common eligibility conditions that apply to it. Other sub-schemes"
            " are not this opportunity. Mark applicability, effective dates, selection "
            "limits, exclusions, renewal differences and source completeness for review."
            " Do not assume an application round is open."
        ),
    )
}
ALLOWED_HOSTS = {"depwd.gov.in", "cdnbbsr.s3waas.gov.in"}


class FetchFailure(Exception):
    def __init__(self, code: str, status: int | None = None):
        self.code, self.status = code, status


@dataclass
class Fetched:
    raw: bytes
    media_type: str
    pages: list[dict]
    metadata: dict


def allowed_url(url: str):
    value = urlsplit(url)
    if (
        value.scheme != "https"
        or value.hostname not in ALLOWED_HOSTS
        or value.username
        or value.password
        or value.port not in (None, 443)
    ):
        raise FetchFailure("url_not_allowlisted")


def request(client: httpx.Client, url: str, *, allow_redirects=True):
    allowed_url(url)
    for redirect in range(4):
        for attempt in range(3):
            try:
                with client.stream("GET", url, headers={"User-Agent": USER_AGENT}) as response:
                    # A rate-limit response stops this run; do not retry ahead of Retry-After.
                    if response.status_code in (500, 502, 503, 504) and attempt < 2:
                        time.sleep(0.5 * (2**attempt))
                        continue
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise FetchFailure("response_too_large", response.status_code)
                        chunks.append(chunk)
                    result = httpx.Response(
                        response.status_code,
                        headers=response.headers,
                        content=b"".join(chunks),
                        request=response.request,
                    )
                    break
            except httpx.TimeoutException:
                if attempt == 2:
                    raise FetchFailure("timeout") from None
                time.sleep(0.5 * (2**attempt))
            except httpx.HTTPError:
                raise FetchFailure("network_or_tls_error") from None
        if result.is_redirect:
            if not allow_redirects:
                raise FetchFailure("robots_redirect_requires_review", result.status_code)
            next_url = str(result.url.join(result.headers.get("location", "")))
            allowed_url(next_url)
            # A redirect to a different host must be registered explicitly, not followed.
            if urlsplit(next_url).netloc != urlsplit(url).netloc:
                raise FetchFailure("cross_host_redirect_requires_review", result.status_code)
            url = next_url
            continue
        return result
    raise FetchFailure("too_many_redirects")


def check_robots(client: httpx.Client, url: str):
    parsed = urlsplit(url)
    response = request(
        client, f"{parsed.scheme}://{parsed.netloc}/robots.txt", allow_redirects=False
    )
    if response.status_code == 404:
        return {"robots_status": 404, "robots_policy": "not_present"}
    if response.status_code != 200 or "<html" in response.text[:1000].lower():
        raise FetchFailure("robots_unavailable", response.status_code)
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    if not parser.can_fetch(USER_AGENT, url):
        raise FetchFailure("robots_disallowed")
    delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0
    if delay > 60:
        raise FetchFailure("crawl_delay_requires_scheduled_job")
    if delay:
        time.sleep(delay)
    return {"robots_status": 200, "robots_policy": "allowed", "crawl_delay": delay}


def parse(raw: bytes, media_type: str) -> list[dict]:
    if raw.startswith(b"%PDF-"):
        try:
            document = PdfReader(io.BytesIO(raw))
            if document.is_encrypted or len(document.pages) > 100:
                raise FetchFailure("pdf_requires_review")
            pages = [
                {"page": index + 1, "text": page.extract_text()[:100000]}
                for index, page in enumerate(document.pages)
            ]
        except FetchFailure:
            raise
        except Exception:
            raise FetchFailure("pdf_parse_failed") from None
    elif "html" in media_type:
        soup = BeautifulSoup(raw, "html.parser")
        for node in soup.select("script,style,nav,header,footer"):
            node.decompose()
        main = soup.find("main") or soup
        pages = [{"page": 1, "text": main.get_text(" ", strip=True)[:200000]}]
    else:
        raise FetchFailure("unsupported_media_type")
    if sum(len(p["text"]) for p in pages) < 200:
        raise FetchFailure("empty_or_challenge_page")
    if any(
        marker in pages[0]["text"].lower()
        for marker in ["verify you are human", "complete the captcha", "access denied"]
    ):
        raise FetchFailure("blocked_or_captcha")
    return pages


def fetch(adapter: Adapter, client: httpx.Client | None = None) -> Fetched:
    own = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(15, read=30), follow_redirects=False, trust_env=False
    )
    try:
        import hashlib

        pages, bodies, documents = [], [], []
        for url in (adapter.url, *adapter.amendment_urls):
            policy = check_robots(client, url)
            response = request(client, url)
            if response.status_code != 200:
                raise FetchFailure("source_http_error", response.status_code)
            media = response.headers.get("content-type", "").split(";")[0]
            parsed = parse(response.content, media)
            pages.extend([{**page, "source_url": url} for page in parsed])
            bodies.append(len(response.content).to_bytes(8, "big") + response.content)
            documents.append(
                {
                    **policy,
                    "url": url,
                    "content_hash": hashlib.sha256(response.content).hexdigest(),
                    "byte_count": len(response.content),
                    "etag": response.headers.get("etag"),
                    "last_modified": response.headers.get("last-modified"),
                }
            )
            if adapter.amendment_urls and url != adapter.amendment_urls[-1]:
                time.sleep(1)
        if sum(len(p["text"]) for p in pages) > 500000:
            raise FetchFailure("document_bundle_too_large")
        return Fetched(
            b"".join(bodies),
            "application/x-source-bundle",
            pages,
            {"http_status": 200, "documents": documents, "context_url": adapter.context_url},
        )
    finally:
        if own:
            client.close()
