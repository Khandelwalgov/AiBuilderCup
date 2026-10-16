"""Allowlisted, sequential, robots-aware HTTP. No ambient proxy or credentials."""

import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from .schemas import SourceSpec

USER_AGENT = "UnclaimedCorpus/1.0 (bounded public-document research)"
CHALLENGES = (
    "verify you are human",
    "complete the captcha",
    "access denied",
    "request rejected",
    "enable javascript and cookies to continue",
    "the requested url was rejected",
    "checking your browser",
    "captcha validation",
    "automated access is prohibited",
)


class AcquisitionError(Exception):
    def __init__(self, code, status=None, detail=None):
        self.code, self.status, self.detail = code, status, detail
        super().__init__(code)


def canonical(url: str) -> str:
    p = urlsplit(url)
    # Preserve query order/values: signed URLs and document IDs must not be rewritten.
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))


def allowed(url: str, source: SourceSpec, *, robots=False):
    try:
        p = urlsplit(url)
        if (
            p.scheme != "https"
            or p.hostname not in source.allowed_hosts
            or p.username
            or p.password
            or p.port not in (None, 443)
            or "\\" in url
            or any(ord(c) < 32 for c in url)
        ):
            raise ValueError()
        # Normalize decoded paths before comparing CDN prefixes (including traversal).
        from posixpath import normpath
        from urllib.parse import unquote

        path = normpath(unquote(p.path))
        prefixes = source.path_prefixes.get(p.hostname)
        if (
            prefixes
            and not (robots and path == "/robots.txt")
            and not any(path.startswith(prefix) for prefix in prefixes)
        ):
            raise ValueError()
    except ValueError:
        raise AcquisitionError("official_host_or_path_restriction") from None


def challenge(raw: bytes):
    text = raw[:200000].decode("utf-8", errors="replace").lower()
    if any(marker in text for marker in CHALLENGES):
        raise AcquisitionError("manual_access_required")


@dataclass
class Payload:
    raw: bytes
    final_url: str
    headers: dict
    status: int
    policy: dict


class Fetcher:
    def __init__(
        self,
        client,
        *,
        max_bytes,
        max_total_bytes,
        max_requests,
        delay=1.0,
        progress=None,
        sleep=time.sleep,
        monotonic=time.monotonic,
    ):
        self.client = client
        self.max_bytes = max_bytes
        self.max_total_bytes = max_total_bytes
        self.max_requests = max_requests
        self.delay, self.sleep, self.monotonic = delay, sleep, monotonic
        self.progress = progress or (lambda requests, size: None)
        self.requests = self.bytes = 0
        self.robots = {}
        self.next_request = {}
        self.blocked_hosts = {}

    def _request(self, url, source, *, robots=False):
        allowed(url, source, robots=robots)
        host = urlsplit(url).hostname
        if host in self.blocked_hosts:
            raise AcquisitionError("host_paused", detail=self.blocked_hosts[host])
        for attempt in range(3):
            if self.requests >= self.max_requests or self.bytes >= self.max_total_bytes:
                raise AcquisitionError("run_budget_exhausted")
            self.sleep(max(0, self.next_request.get(host, 0) - self.monotonic()))
            self.requests += 1
            self.progress(self.requests, self.bytes)
            try:
                with self.client.stream("GET", url, headers={"User-Agent": USER_AGENT}) as r:
                    status = r.status_code
                    if status == 429:
                        self.blocked_hosts[host] = r.headers.get("retry-after", "next run")
                        raise AcquisitionError("rate_limited", status, self.blocked_hosts[host])
                    if status in (401, 403):
                        self.blocked_hosts[host] = str(status)
                        raise AcquisitionError("manual_access_required", status)
                    if status in (500, 502, 503, 504) and attempt < 2:
                        retry = r.headers.get("retry-after")
                        if retry:
                            self.blocked_hosts[host] = retry
                            raise AcquisitionError("retry_after_deferred", status, retry)
                        self.sleep(2**attempt)
                        continue
                    limit = min(self.max_bytes, 512 * 1024) if robots else self.max_bytes
                    try:
                        declared = int(r.headers.get("content-length", "0"))
                    except ValueError:
                        declared = 0
                    if declared > limit:
                        raise AcquisitionError("file_too_large", status)
                    chunks, size = [], 0
                    for chunk in r.iter_bytes(chunk_size=65536):
                        self.bytes += len(chunk)
                        size += len(chunk)
                        self.progress(self.requests, self.bytes)
                        if self.bytes > self.max_total_bytes:
                            raise AcquisitionError("run_budget_exhausted")
                        if size > limit:
                            raise AcquisitionError("file_too_large", status)
                        chunks.append(chunk)
                    return status, dict(r.headers), b"".join(chunks)
            except httpx.TimeoutException:
                if attempt == 2:
                    raise AcquisitionError("timeout") from None
                self.sleep(2**attempt)
            except httpx.HTTPError as exc:
                raise AcquisitionError("network_or_tls_error", detail=type(exc).__name__) from None
            finally:
                policy = self.robots.get(host, ({}, None))[0]
                delay = max(self.delay, policy.get("crawl_delay", 0))
                self.next_request[host] = self.monotonic() + delay
        raise AcquisitionError("retry_exhausted")

    def policy(self, url, source):
        allowed(url, source)
        p = urlsplit(url)
        if p.hostname not in self.robots:
            robots_url = f"https://{p.netloc}/robots.txt"
            status, headers, raw = self._request(robots_url, source, robots=True)
            if status == 404:
                policy, parser = {"robots_status": 404, "robots_policy": "not_present"}, None
            elif status == 200:
                challenge(raw)
                if b"<html" in raw[:2000].lower() or b"<!doctype" in raw[:2000].lower():
                    raise AcquisitionError("robots_invalid_html", status)
                parser = RobotFileParser()
                parser.parse(raw.decode("utf-8", errors="replace").splitlines())
                delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0
                rate = parser.request_rate(USER_AGENT) or parser.request_rate("*")
                if rate:
                    delay = max(delay, rate.seconds / rate.requests)
                if delay > 60:
                    raise AcquisitionError("crawl_delay_requires_schedule")
                policy = {"robots_status": status, "robots_policy": "allowed", "crawl_delay": delay}
            else:
                raise AcquisitionError(
                    "robots_unavailable_or_redirect", status, headers.get("location")
                )
            self.robots[p.hostname] = policy, parser
            self.next_request[p.hostname] = self.monotonic() + max(
                self.delay, policy.get("crawl_delay", 0)
            )
        policy, parser = self.robots[p.hostname]
        if parser and not parser.can_fetch(USER_AGENT, url):
            raise AcquisitionError("robots_disallowed")
        return policy

    def fetch(self, url, source):
        redirects = []
        for _ in range(5):
            policy = self.policy(url, source)
            status, headers, raw = self._request(url, source)
            if status in (301, 302, 303, 307, 308):
                target = canonical(urljoin(url, headers.get("location", "")))
                allowed(target, source)
                redirects.append({"url": url, "status": status, "location": target})
                url = target
                continue
            if status != 200:
                code = "listing_unavailable" if status in (404, 410) else "http_error"
                raise AcquisitionError(code, status)
            if not raw.startswith(b"%PDF-"):
                challenge(raw)
            selected = {
                key: headers.get(key)
                for key in ("content-type", "etag", "last-modified", "date", "content-length")
            }
            return Payload(raw, url, selected, status, {**policy, "redirects": redirects})
        raise AcquisitionError("too_many_redirects")
