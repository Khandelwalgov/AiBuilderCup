"""Offline collector tests; fixture bytes are synthetic and never counted as live coverage."""

import hashlib
import io
import json

import httpx
import pytest
from pypdf import PdfWriter

from opportunity_platform.corpus.cli import collect, load_sources, metrics
from opportunity_platform.corpus.discovery import feed_links, html_links, validate
from opportunity_platform.corpus.network import AcquisitionError, Fetcher, allowed
from opportunity_platform.corpus.schemas import SourceSpec
from opportunity_platform.corpus.store import Store


def pdf(pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(100, 100)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


def spec(**kwargs):
    return SourceSpec(
        key="test",
        authority="Synthetic Government Test Authority",
        jurisdiction="India",
        category="scholarships",
        seeds=["https://test.gov.in/index"],
        allowed_hosts=["test.gov.in"],
        access="public",
        access_note="Offline synthetic transport only",
        **kwargs,
    )


def options(**kwargs):
    return {
        "max_documents": 10,
        "max_requests": 100,
        "max_file_bytes": 100000,
        "max_total_bytes": 1000000,
        "delay": 0,
        **kwargs,
    }


def transport(raw, listing=None):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if request.url.path == "/index":
            return httpx.Response(
                200,
                text=listing or '<a href="/a.pdf">Test scholarship</a>',
                headers={"content-type": "text/html"},
            )
        return httpx.Response(200, content=raw, headers={"content-type": "application/pdf"})

    return httpx.MockTransport(handler)


def test_new_unchanged_changed_and_integrity(tmp_path):
    store = Store(tmp_path)
    source = spec()
    for raw in (pdf(), pdf(), pdf(2), pdf()):
        with httpx.Client(transport=transport(raw)) as client:
            collect(store, [source], options(), client)
    assert [r[0] for r in store.db.execute("SELECT status FROM events WHERE kind='document'")] == [
        "new",
        "unchanged",
        "updated",
        "updated",
    ]
    snapshots = list(store.db.execute("SELECT * FROM snapshots ORDER BY downloaded_at"))
    assert len(snapshots) == 3
    assert snapshots[1]["previous_id"] == snapshots[0]["id"]
    assert snapshots[2]["previous_id"] == snapshots[1]["id"]
    assert len(list((tmp_path / "blobs").glob("*/*"))) == 2
    assert store.verify(validate) == {"unique_blobs_checked": 2, "errors": []}
    records = [json.loads(line) for line in (tmp_path / "manifest.jsonl").read_text().splitlines()]
    assert records[0]["discoveries"][0]["issuing_authority"] == source.authority
    assert records[0]["sha256"] == hashlib.sha256(pdf()).hexdigest()
    (tmp_path / snapshots[0]["blob_path"]).write_bytes(b"corrupt")
    assert store.verify(validate)["errors"]
    store.close()


def test_duplicate_links_and_identical_content(tmp_path):
    listing = '<a href="/a.pdf">One</a><a href="/a.pdf#x">Again</a><a href="/b.pdf">Two</a>'
    store = Store(tmp_path)
    with httpx.Client(transport=transport(pdf(), listing)) as client:
        run = collect(store, [spec()], options(), client)
    report = metrics(store, run)
    assert report["successful_document_fetches"] == 2
    assert report["distinct_content_in_run"] == 1
    assert report["change_counts"] == {"new": 1, "duplicate": 1}
    assert store.db.execute("SELECT count(*) FROM tasks WHERE kind='document'").fetchone()[0] == 2
    store.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://test.gov.in/a.pdf",
        "https://evil.gov.in/a.pdf",
        "https://127.0.0.1/a.pdf",
        "https://test.gov.in.evil.com/a.pdf",
        "https://a:b@test.gov.in/a.pdf",
        "https://test.gov.in:444/a.pdf",
        "https://test.gov.in\\@evil.com/a.pdf",
    ],
)
def test_official_host_restrictions(url):
    with pytest.raises(AcquisitionError, match="official_host"):
        allowed(url, spec())


def test_cdn_scope_and_robots_exception():
    source = spec().model_copy(
        update={
            "allowed_hosts": ["cdnbbsr.s3waas.gov.in"],
            "path_prefixes": {"cdnbbsr.s3waas.gov.in": ["/s3issuer/"]},
        }
    )
    allowed("https://cdnbbsr.s3waas.gov.in/s3issuer/a.pdf", source)
    allowed("https://cdnbbsr.s3waas.gov.in/robots.txt", source, robots=True)
    for path in ("/s3other/a.pdf", "/s3issuer/%2e%2e/s3other/a.pdf", "/robots.txt"):
        with pytest.raises(AcquisitionError):
            allowed("https://cdnbbsr.s3waas.gov.in" + path, source)


def fetch_with(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return client, Fetcher(
        client,
        max_bytes=kwargs.get("max_bytes", 10000),
        max_total_bytes=20000,
        max_requests=20,
        delay=0,
        sleep=lambda _: None,
    )


@pytest.mark.parametrize(
    "status,code",
    [(403, "manual_access_required"), (429, "rate_limited"), (404, "listing_unavailable")],
)
def test_failures_preserve_history_and_rate_limit(tmp_path, status, code):
    store = Store(tmp_path)
    with httpx.Client(transport=transport(pdf())) as client:
        collect(store, [spec()], options(), client)
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/index":
            return httpx.Response(200, text='<a href="/a.pdf">Scheme</a>')
        return httpx.Response(status, headers={"retry-after": "120"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        run = collect(store, [spec()], options(), client)
    assert metrics(store, run)["failures"][0]["status"] == code
    assert calls.count("/a.pdf") == 1
    assert store.db.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 1
    store.close()


def test_redirect_and_broken_redirect():
    def handler(request):
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if path == "/a":
            return httpx.Response(302, headers={"location": "/b.pdf"})
        if path == "/evil":
            return httpx.Response(302, headers={"location": "https://evil.com/secret"})
        if path == "/loop":
            return httpx.Response(302, headers={"location": "/loop"})
        return httpx.Response(200, content=pdf())

    client, fetcher = fetch_with(handler)
    assert fetcher.fetch("https://test.gov.in/a", spec()).final_url.endswith("/b.pdf")
    with pytest.raises(AcquisitionError, match="official_host"):
        fetcher.fetch("https://test.gov.in/evil", spec())
    with pytest.raises(AcquisitionError, match="too_many_redirects"):
        fetcher.fetch("https://test.gov.in/loop", spec())
    client.close()


@pytest.mark.parametrize(
    "raw,media,url,code",
    [
        (b"%PDF-bad", "application/pdf", "/a.pdf", "invalid_pdf"),
        (b"<html>not pdf</html>", "text/html", "/a.pdf", "invalid_pdf"),
        (b"<html>Verify you are human</html>", "text/html", "/a", "manual_access_required"),
        (b"<html><script>empty()</script></html>", "text/html", "/a", "empty_or_javascript"),
    ],
)
def test_validation(raw, media, url, code):
    with pytest.raises(AcquisitionError, match=code):
        validate(raw, media, url)


def test_oversized_and_robots_denied():
    client, f = fetch_with(lambda r: httpx.Response(200, content=b"x" * 200), max_bytes=100)
    with pytest.raises(AcquisitionError, match="file_too_large"):
        f.fetch("https://test.gov.in/a.pdf", spec())
    client.close()
    client, f = fetch_with(lambda r: httpx.Response(200, text="User-agent: *\nDisallow: /"))
    with pytest.raises(AcquisitionError, match="robots_disallowed"):
        f.fetch("https://test.gov.in/a.pdf", spec())
    assert f.requests == 1
    client.close()


def test_partial_run_resume(tmp_path):
    store = Store(tmp_path)
    calls = []
    base = transport(pdf())

    def handler(request):
        calls.append(request.url.path)
        if request.url.path == "/a.pdf" and calls.count("/a.pdf") == 1:
            raise KeyboardInterrupt()
        return base.handler(request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        run = collect(store, [spec()], options(), client)
        assert metrics(store, run)["pending_tasks"] == 1
        collect(store, [spec()], options(), client, resume=run)
    assert calls.count("/index") == 1
    assert metrics(store, run)["successful_document_fetches"] == 1
    store.close()


def test_expiry_amendment_and_feed_association():
    raw = json.dumps(
        {
            "items": [
                {
                    "url": "/a.pdf",
                    "title": "Synthetic tender amendment",
                    "closes_on": "2020-01-01",
                    "relation": "amendment",
                    "related_urls": ["https://test.gov.in/original.pdf"],
                    "association_basis": "explicit_feed_reference",
                }
            ]
        }
    ).encode()
    candidates, pages = feed_links(raw, "https://test.gov.in/feed", spec())
    assert candidates[0].closes_on.isoformat() == "2020-01-01"
    assert candidates[0].relation == "amendment"
    assert candidates[0].related_urls == ["https://test.gov.in/original.pdf"]
    assert pages == []
    docs, _ = html_links(
        b'<table><tr><td>Scheme corrigendum</td><td><a href="/a.pdf">View</a>'
        b'<a href="/original.pdf">Original</a></td></tr></table>',
        "https://test.gov.in/index",
        spec(),
    )
    assert docs[0].relation == "amendment"
    assert docs[0].association_basis == "same_index_row_unverified"


def test_manual_source_no_requests(tmp_path):
    store = Store(tmp_path)
    source = spec().model_copy(update={"access": "manual_access_required"})
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("network prohibited"))
    ) as c:
        run = collect(store, [source], options(), c)
    assert metrics(store, run)["sources_attempted_network"] == 0
    store.close()


def test_registry_is_valid():
    from opportunity_platform.corpus.cli import REPO

    assert len(load_sources(REPO / "data/corpus/sources.json")) >= 20
