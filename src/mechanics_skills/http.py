"""
Universal HTTP client for mechanics-agent-skills.
Zero external dependencies by default (urllib.request).
Supports optional httpx transport when available.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, Optional, Union

from mechanics_skills.config import (
    DEFAULT_RATE_LIMITS,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    settings,
)
from mechanics_skills.errors import HTTPError, RateLimitError

logger = logging.getLogger("mechanics_skills.http")


class HTTPResponse:
    """Standardized HTTP response wrapper."""

    def __init__(
        self,
        status_code: int,
        headers: Mapping[str, str],
        content: bytes,
        url: str = "",
    ):
        self.status_code = status_code
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.content = content
        self.url = url
        self._text: Optional[str] = None
        self._json: Optional[Any] = None

    @property
    def text(self) -> str:
        if self._text is None:
            # Handle encoding
            encoding = "utf-8"
            content_type = self.headers.get("content-type", "")
            if "charset=" in content_type:
                encoding = content_type.split("charset=")[-1].split(";")[0].strip()
            try:
                self._text = self.content.decode(encoding, errors="replace")
            except Exception:
                self._text = self.content.decode("utf-8", errors="replace")
        return self._text

    def json(self) -> Any:
        if self._json is None:
            self._json = json.loads(self.text)
        return self._json

    def raise_for_status(self) -> None:
        """Raise HTTPError if status code indicates an error (>= 400)."""
        if self.status_code == 429:
            retry_after = None
            if "retry-after" in self.headers:
                try:
                    retry_after = float(self.headers["retry-after"])
                except ValueError:
                    pass
            raise RateLimitError(
                f"Rate limited (429) for {self.url}",
                retry_after=retry_after,
                details=self.text[:500],
            )
        if self.status_code >= 400:
            raise HTTPError(
                f"HTTP {self.status_code} error for {self.url}",
                status_code=self.status_code,
                url=self.url,
                body=self.text[:500],
            )


class RateLimiter:
    """Per-domain rate limiter using min-interval pacing."""

    def __init__(self, limits: Optional[Dict[str, float]] = None):
        self.limits = limits or dict(DEFAULT_RATE_LIMITS)
        self.default_delay = 0.2  # 5 req/sec default
        self._last_times: Dict[str, float] = {}

    def wait(self, domain: str) -> None:
        min_delay = 1.0 / self.limits.get(domain, 1.0 / self.default_delay)
        current = time.time()
        last = self._last_times.get(domain, 0.0)
        elapsed = current - last
        if elapsed < min_delay:
            sleep_time = min_delay - elapsed
            time.sleep(sleep_time)
        self._last_times[domain] = time.time()


class HTTPClient:
    """
    Universal HTTP Client with rate-limiting, exponential backoff,
    and zero third-party dependencies (urllib-based by default).
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        rate_limiter: Optional[RateLimiter] = None,
        backend: Optional[str] = None,
    ):
        self.user_agent = user_agent or settings.user_agent or DEFAULT_USER_AGENT
        self.timeout = timeout if timeout is not None else settings.timeout
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.rate_limiter = rate_limiter or RateLimiter()
        self.backend = backend or settings.http_backend

        # Optional httpx client initialization if requested & available
        self._httpx_client = None
        if self.backend in ("httpx", "auto"):
            try:
                import httpx
                # Only use httpx if backend is explicitly 'httpx' or auto is accepted
                if self.backend == "httpx":
                    self._httpx_client = httpx.Client(
                        headers={"User-Agent": self.user_agent},
                        timeout=self.timeout,
                        follow_redirects=True,
                    )
            except ImportError:
                pass

    def _prepare_url(self, url: str, params: Optional[Mapping[str, Any]] = None) -> str:
        if not params:
            return url
        # Filter None values and encode
        query_pairs = []
        for k, v in params.items():
            if v is not None:
                query_pairs.append((k, str(v)))
        encoded_query = urllib.parse.urlencode(query_pairs)
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{encoded_query}" if encoded_query else url

    def request(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        data: Optional[bytes] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> HTTPResponse:
        full_url = self._prepare_url(url, params)
        parsed = urllib.parse.urlparse(full_url)
        domain = parsed.netloc

        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
        }
        if headers:
            req_headers.update(headers)

        req_timeout = timeout if timeout is not None else self.timeout
        retries = max_retries if max_retries is not None else self.max_retries

        for attempt in range(retries + 1):
            self.rate_limiter.wait(domain)
            try:
                # Use urllib transport
                req = urllib.request.Request(
                    full_url,
                    data=data,
                    headers=req_headers,
                    method=method.upper(),
                )
                with urllib.request.urlopen(req, timeout=req_timeout) as resp:
                    resp_headers = dict(resp.info())
                    content = resp.read()
                    status_code = resp.status if hasattr(resp, "status") else resp.getcode()
                    return HTTPResponse(
                        status_code=status_code,
                        headers=resp_headers,
                        content=content,
                        url=full_url,
                    )

            except urllib.error.HTTPError as e:
                status_code = e.code
                resp_headers = dict(e.headers) if hasattr(e, "headers") else {}
                try:
                    content = e.read()
                except Exception:
                    content = b""

                resp = HTTPResponse(
                    status_code=status_code,
                    headers=resp_headers,
                    content=content,
                    url=full_url,
                )

                # Retry on 429 or 5xx server errors
                if (status_code == 429 or status_code >= 500) and attempt < retries:
                    wait_time = 2 ** attempt
                    # Check Retry-After header if available
                    if "retry-after" in resp.headers:
                        try:
                            wait_time = max(float(resp.headers["retry-after"]), 1.0)
                        except ValueError:
                            pass
                    logger.warning(
                        f"HTTP {status_code} for {full_url}. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{retries})..."
                    )
                    time.sleep(wait_time)
                    continue

                # Don't retry other 4xx errors
                return resp

            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt < retries:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Connection/Timeout error: {e} for {full_url}. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{retries})..."
                    )
                    time.sleep(wait_time)
                    continue
                raise HTTPError(f"Request failed after {retries} retries: {e}", url=full_url) from e

        raise HTTPError(f"Request failed after {retries} retries", url=full_url)

    def get(
        self,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> HTTPResponse:
        return self.request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )

    def get_json(
        self,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> Any:
        resp = self.get(
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )
        resp.raise_for_status()
        return resp.json()

    def get_bytes(
        self,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> bytes:
        resp = self.get(
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )
        resp.raise_for_status()
        return resp.content


# Shared global default client
default_client = HTTPClient()

