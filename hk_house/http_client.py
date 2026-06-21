"""Anti-blocking HTTP client shared by all fetchers.

Defences against being blocked:
  * realistic rotating browser User-Agents + sane default headers
  * HTTP/2 and a persistent cookie jar (mimics a real browser session)
  * polite randomised delay between requests (rate limiting + jitter)
  * exponential backoff with jitter on 429 / 5xx / network errors
  * honours the server's ``Retry-After`` header on 429 / 503
  * optional proxy rotation

Use it as a context manager:

    with HttpClient(base_headers={"Referer": "https://..."}) as client:
        resp = client.get(url)
        data = client.post_json(url, json=body)
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from .config import NETWORK, USER_AGENTS

log = logging.getLogger("hkhouse.http")

# Status codes worth retrying (transient / throttling).
RETRY_STATUS = {429, 500, 502, 503, 504}


class BlockedError(RuntimeError):
    """Raised when a response looks like a hard block (e.g. 403 challenge)."""


class HttpClient:
    def __init__(
        self,
        base_headers: dict[str, str] | None = None,
        cookies: dict[str, str] | str | None = None,
    ) -> None:
        self._net = NETWORK
        self._proxies = list(self._net.proxies)
        self._proxy_idx = 0
        self._last_request_ts = 0.0

        headers = self._default_headers()
        if base_headers:
            headers.update(base_headers)

        # Accept a raw "Cookie:" string (as copied from the browser) or a dict.
        cookie_jar = None
        if isinstance(cookies, str):
            cookie_jar = self._parse_cookie_string(cookies)
        elif isinstance(cookies, dict):
            cookie_jar = cookies

        self._client = httpx.Client(
            http2=True,
            headers=headers,
            cookies=cookie_jar,
            timeout=self._net.timeout,
            follow_redirects=True,
            proxy=self._next_proxy(),
        )

    # -- public API ---------------------------------------------------------
    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self._request("GET", url, **kwargs)

    def post_json(self, url: str, json: Any, **kwargs: Any) -> httpx.Response:
        return self._request("POST", url, json=json, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- internals ----------------------------------------------------------
    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._net.max_retries + 1):
            self._throttle()
            # Rotate UA per request to look less scripted.
            kwargs.setdefault("headers", {})
            kwargs["headers"] = {**kwargs["headers"], "User-Agent": random.choice(USER_AGENTS)}
            try:
                resp = self._client.request(method, url, **kwargs)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                wait = self._backoff(attempt)
                log.warning("%s %s network error (%s); retry in %.1fs", method, url, exc, wait)
                self._rotate_proxy()
                time.sleep(wait)
                continue

            if resp.status_code in RETRY_STATUS:
                last_exc = httpx.HTTPStatusError(
                    f"{resp.status_code}", request=resp.request, response=resp
                )
                wait = self._retry_after(resp) or self._backoff(attempt)
                log.warning(
                    "%s %s -> %s; retry %d/%d in %.1fs",
                    method, url, resp.status_code, attempt + 1, self._net.max_retries, wait,
                )
                if resp.status_code == 429:
                    self._rotate_proxy()
                time.sleep(wait)
                continue

            if resp.status_code == 403:
                # Likely a WAF / Cloudflare challenge -- retrying rarely helps
                # without fresh cookies, so surface it loudly.
                raise BlockedError(
                    f"403 on {url}: blocked (WAF/Cloudflare?). "
                    "Supply fresh browser cookies via config."
                )

            resp.raise_for_status()
            return resp

        raise BlockedError(f"{method} {url} failed after retries") from last_exc

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        delay = self._net.min_delay + random.uniform(0, self._net.max_jitter)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_request_ts = time.monotonic()

    def _backoff(self, attempt: int) -> float:
        raw = self._net.backoff_base ** attempt
        return min(raw, self._net.backoff_max) + random.uniform(0, 1.0)

    @staticmethod
    def _retry_after(resp: httpx.Response) -> float | None:
        val = resp.headers.get("Retry-After")
        if val and val.isdigit():
            return float(val)
        return None

    def _next_proxy(self) -> str | None:
        if not self._proxies:
            return None
        return self._proxies[self._proxy_idx % len(self._proxies)]

    def _rotate_proxy(self) -> None:
        if not self._proxies:
            return
        self._proxy_idx += 1
        # httpx binds the proxy at client construction, so rebuild the transport.
        old = self._client
        self._client = httpx.Client(
            http2=True,
            headers=old.headers,
            cookies=old.cookies,
            timeout=self._net.timeout,
            follow_redirects=True,
            proxy=self._next_proxy(),
        )
        old.close()
        log.info("rotated to proxy %s", self._next_proxy())

    @staticmethod
    def _default_headers() -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    @staticmethod
    def _parse_cookie_string(raw: str) -> dict[str, str]:
        jar: dict[str, str] = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                jar[k.strip()] = v.strip()
        return jar
