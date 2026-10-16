"""Offline, read-only original archive audit and bounded PDF/HTML extraction."""

import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, NavigableString
from pypdf import PdfReader

from opportunity_platform.corpus.network import allowed
from opportunity_platform.corpus.schemas import ManifestRecord, SourceSpec
from opportunity_platform.ingestion.schemas import normalize

from .contracts import Clause

MAX_BYTES = 20 * 1024**2
MAX_TEXT = 2_000_000
TEXT_VERSION = "archive-text-v1"
NORMATIVE = re.compile(
    r"(?i)\b(shall|must|eligible|eligibility|income|beneficiar|criteria|deadline|"
    r"not exceeding|required|amend|exclud|subsid|assistance|loan|grant|renewal)\w*"
    r"|पात्र|आय|आवश्यक|अनिवार्य|अंतिम|संशोधन|अनुदान|सहायता"
)
LEGACY = re.compile(r"jktLFkku|ljdkj|foHkkx|funsZ|Nk=o|vf/kdk|;kstuk|ik=rk")


@dataclass
class Audited:
    record: ManifestRecord
    corrected_title: str
    document_type: str
    pages: list[dict]
    clauses: list[Clause]
    flags: list[str] = field(default_factory=list)
    technically_ingestible: bool = False
    needs_ocr: bool = False
    suitable_for_extraction: bool = False
    document_issuer: str | None = None
    issuer_evidence: dict | None = None

    def public(self):
        return {
            "snapshot_id": self.record.snapshot_id,
            "document_id": self.record.document_id,
            "sha256": self.record.sha256,
            "source_url": self.record.canonical_source_url,
            "original_titles": list(
                dict.fromkeys(d.get("title", "") for d in self.record.discoveries)
            ),
            "corrected_title": self.corrected_title,
            "title_basis": "index_label_cleanup_or_html_heading_not_legal_verification",
            "document_type": self.document_type,
            "technically_ingestible": self.technically_ingestible,
            "needs_ocr": self.needs_ocr,
            "questionable_metadata": any(
                f.startswith("issuer_") or f in {"metadata_layout_title", "metadata_generic_title"}
                for f in self.flags
            ),
            "suitable_for_candidate_extraction": self.suitable_for_extraction,
            "document_issuer": self.document_issuer,
            "issuer_evidence": self.issuer_evidence,
            "index_publishers": list(
                dict.fromkeys(
                    d.get("issuing_authority", "unknown") for d in self.record.discoveries
                )
            ),
            "flags": self.flags,
            "page_or_section_count": len(self.pages),
            "text_characters": sum(len(p["text"]) for p in self.pages),
            "material_clause_count": len(self.clauses),
            "page_quality": [
                {k: p[k] for k in ("page", "section", "quality") if k in p} for p in self.pages
            ],
        }


def load_manifest(path):
    records = [
        ManifestRecord.model_validate_json(line)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
    ids = [r.snapshot_id for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate snapshot identities in manifest")
    return records


def original_bytes(root, record, registry):
    path = (Path(root) / record.blob_path).resolve()
    blob_root = (Path(root) / "blobs").resolve()
    if not path.is_relative_to(blob_root) or path.is_symlink():
        raise ValueError("blob_path_outside_archive")
    if path.stat().st_size != record.size_bytes or record.size_bytes > MAX_BYTES:
        raise ValueError("archive_size_mismatch_or_limit")
    if not record.discoveries:
        raise ValueError("missing_source_attribution")
    for association in record.discoveries:
        spec = registry.get(association.get("source_key"))
        if not spec or spec.access != "public":
            raise ValueError("source_not_authorized_for_archive_import")
        allowed(record.canonical_source_url, spec)
        allowed(record.final_url, spec)
        allowed(association["discovery_url"], spec)
    if urlsplit(record.canonical_source_url).hostname != record.originating_domain:
        raise ValueError("origin_domain_mismatch")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record.sha256:
        raise ValueError("archive_hash_mismatch")
    return raw


def quality(text):
    letters = sum(c.isalpha() for c in text)
    if letters < 40:
        return "scanned_or_insufficient_text"
    if LEGACY.search(text) or text.count("\ufffd") > max(3, letters // 100):
        return "unreadable_or_legacy_encoding"
    return "readable_text_unverified"


def extract_pages(raw, record):
    url = record.canonical_source_url
    if record.format == "pdf":
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 500:
            raise ValueError("unsupported_pdf")
        pages = []
        total = 0
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            total += len(text)
            if total > MAX_TEXT:
                raise ValueError("extracted_text_limit")
            fonts = page.get("/Resources", {}).get("/Font", {})
            if hasattr(fonts, "get_object"):
                fonts = fonts.get_object()
            names = [str(font.get_object().get("/BaseFont", "")) for font in fonts.values()]
            text_quality = quality(text)
            if re.search(r"(?i)kruti|devlys|chanakya|shree|dv-tt", " ".join(names)):
                devanagari = sum("\u0900" <= char <= "\u097f" for char in text)
                if devanagari < max(20, len(text) // 10):
                    text_quality = "unreadable_or_legacy_encoding"
            pages.append(
                {
                    "page": index + 1,
                    "source_url": url,
                    "text": text,
                    "quality": text_quality,
                    "fonts": names,
                    "provenance": "pdf_physical_page",
                }
            )
        return pages
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.select(
        "script,style,nav,header,footer,iframe,noscript,input,button,select,textarea"
    ):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    sections, heading, pieces = [], "HTML body", []
    # Each text node once; headings supply deterministic section provenance.
    for node in main.descendants:
        if not isinstance(node, NavigableString) or not node.strip():
            continue
        text = normalize(str(node))
        if node.parent.name in ("h1", "h2", "h3", "h4"):
            if pieces:
                sections.append((heading, "\n".join(pieces)))
                pieces = []
            heading = text
        pieces.append(text)
    if pieces:
        sections.append((heading, "\n".join(pieces)))
    if sum(len(text) for _, text in sections) > MAX_TEXT or len(sections) > 500:
        raise ValueError("html_text_or_section_limit")
    return [
        {
            "page": i + 1,
            "section": heading,
            "source_url": url,
            "text": text,
            "quality": quality(text),
            "provenance": "html_section_ordinal_not_pdf_page",
        }
        for i, (heading, text) in enumerate(sections)
    ]


def clauses_for(pages):
    clauses = []
    for page in pages:
        # Bounded consecutive line blocks; no source text is silently dropped from pages.
        lines, current, blocks = page["text"].splitlines(), [], []
        for line in lines:
            current.append(line)
            if len("\n".join(current)) >= 900 or not line.strip():
                blocks.append("\n".join(current).strip())
                current = []
        if current:
            blocks.append("\n".join(current).strip())
        for index, passage in enumerate(blocks):
            if not passage or not NORMATIVE.search(passage):
                continue
            key = f"{page['source_url']}:{page['page']}:{index}:{passage}"
            clauses.append(
                Clause(
                    id=hashlib.sha256(key.encode()).hexdigest()[:24],
                    source_url=page["source_url"],
                    page=page["page"],
                    section=page.get("section"),
                    passage=passage,
                )
            )
    if len(clauses) > 2000:
        raise ValueError("material_clause_limit")
    return clauses


def clean_title(record, pages):
    titles = [d.get("title", "").strip() for d in record.discoveries if d.get("title")]
    title = titles[0] if titles else "Untitled archived document"
    title = re.sub(r"^\d+\s+", "", title)
    title = re.sub(
        r"\s+(?:Tenders|Guidelines|Orders|Circulars|Others)\s+\d+\s+"
        r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}.*$",
        "",
        title,
    )
    title = re.sub(r"\s+Accessible Version\s*:.*$", "", title, flags=re.I)
    flags = []
    if len(title) > 300 or any(t in title for t in ("Apply Online/E-Services", "SJMS Portal")):
        flags.append("metadata_layout_title")
        if "202406271148090737.pdf" in record.canonical_source_url:
            title = "Citizen Charter (index navigation document)"
        else:
            title = "Archived document — title needs human review"
    title = re.sub(r"\s+Download$", "", title, flags=re.I)
    if title.lower() in {"scheme guidelines pdf file", "view", "download", "guidelines"}:
        possible = []
        for page in pages[:3]:
            possible.extend(
                line.strip()
                for line in page["text"].splitlines()
                if re.search(r"(?i)scheme|initiative|scholarship", line)
                and 10 <= len(line.strip()) <= 220
                and not re.match(r"(?i)^(?:[0-9]|no\.|page\b)", line.strip())
            )
        if possible:
            title = re.sub(r"(?i)^Subject:\s*", "", possible[0])
        else:
            flags.append("metadata_generic_title")
    if len(set(titles)) > 1:
        flags.append("metadata_title_variants_preserved")
    if title != (titles[0] if titles else ""):
        flags.append("metadata_title_corrected")
    if record.format == "html":
        headings = [p["section"] for p in pages if p.get("section") not in (None, "HTML body")]
        if headings and title.lower() in {"scholarship scheme", "hostel scheme"}:
            title = headings[-1][:300]
    return title[:300], flags


def audit_record(record, root, registry):
    result = Audited(record, "Unreviewed archived document", "unclassified", [], [])
    try:
        raw = original_bytes(root, record, registry)
        result.pages = extract_pages(raw, record)
        result.technically_ingestible = bool(result.pages)
        result.corrected_title, result.flags = clean_title(record, result.pages)
        result.needs_ocr = record.format == "pdf" and any(
            p["quality"] != "readable_text_unverified" for p in result.pages
        )
        if result.needs_ocr:
            result.flags.append("ocr_or_encoding_review_required")
        title = result.corrected_title.lower()
        index_only = False
        if record.format == "html":
            index_soup = BeautifulSoup(raw, "html.parser")
            pdf_links = sum(
                ".pdf" in a.get("href", "").lower() for a in index_soup.select("a[href]")
            )
            for node in index_soup.select("a,script,style,nav,header,footer"):
                node.decompose()
            prose = index_soup.get_text(" ", strip=True)
            index_only = (pdf_links > 0 and not NORMATIVE.search(prose)) or not any(
                NORMATIVE.search(p["text"]) for p in result.pages
            )
        if re.search(r"citizen charter|registration of training|telephone|list of trainees", title):
            result.document_type = "irrelevant"
        elif index_only:
            result.document_type = "document_index"
            result.flags.append("index_page_not_substantive_policy_text")
        elif re.search(r"amend|corrigend|addendum|संशोधन", title):
            result.document_type = "amendment"
            result.flags.append("amendment_baseline_and_effect_need_review")
        elif re.search(r"tender|bid|nivida|nib|निविदा", title):
            result.document_type = "tender_notice"
            result.flags.append("deadline_and_actual_tender_issuer_need_review")
        elif re.search(
            r"\b(extension|opening|blacklist|hold|notice)\b|date.*extend|last date", title
        ):
            result.document_type = "general_announcement"
        elif re.search(
            r"guideline|scheme|scholarship|policy|grant|initiative|palanhar|hostel|"
            r"छात्रवृत्ति|दिशा|योजना|अनुदान",
            title,
        ):
            result.document_type = "policy_guideline"
        elif re.search(r"order|extension|opening|blacklist|hold|notice|date|सूचना", title):
            result.document_type = "general_announcement"
        # Exact issuer is never copied from the index owner. Limited explicit header recognition.
        for page in result.pages[:3]:
            match = re.search(
                r"Ministry of (?:Micro,? Small\s*(?:&|and)\s*Medium Enterprises|MSME)",
                page["text"],
                re.I,
            )
            if match:
                result.document_issuer = match.group()
                result.issuer_evidence = {
                    "page": page["page"],
                    "source_url": page["source_url"],
                    "passage": match.group(),
                }
                break
        if not result.document_issuer:
            result.flags.append("issuer_document_attribution_unverified")
        result.clauses = clauses_for(result.pages)
        result.suitable_for_extraction = (
            result.technically_ingestible
            and not result.needs_ocr
            and bool(result.clauses)
            and result.document_type in ("policy_guideline", "tender_notice")
            and "metadata_layout_title" not in result.flags
        )
    except Exception as exc:
        result.flags.append("archive_or_text_failure:" + type(exc).__name__)
    return result


def registry_from(path):
    import json

    return {
        s.key: s
        for s in (SourceSpec.model_validate(row) for row in json.loads(Path(path).read_text()))
    }


def summarize(audited):
    unique = {a.record.sha256: a for a in reversed(audited)}
    documents = list(unique.values())
    return {
        "snapshot_records": len(audited),
        "unique_documents": len(documents),
        "technically_ingestible": sum(a.technically_ingestible for a in documents),
        "needs_ocr_or_encoding_review": sum(a.needs_ocr for a in documents),
        "questionable_metadata": sum(a.public()["questionable_metadata"] for a in documents),
        "suitable_for_candidate_extraction": sum(a.suitable_for_extraction for a in documents),
        "document_types": dict(Counter(a.document_type for a in documents)),
        "by_source": {
            key: {
                "unique_documents": len(rows),
                "suitable": sum(a.suitable_for_extraction for a in rows),
                "needs_ocr": sum(a.needs_ocr for a in rows),
            }
            for key in sorted({a.record.discoveries[0]["source_key"] for a in documents})
            if (rows := [a for a in documents if a.record.discoveries[0]["source_key"] == key])
        },
        "definitions": {
            "technically_ingestible": "Hash/size/source validated; text extraction completed",
            "needs_ocr": "At least one page has insufficient text or detected legacy encoding",
            "questionable_metadata": "Unresolved layout/generic title or exact issuer unverified",
            "suitable": "Readable policy/tender with material clauses; human review required",
        },
    }
