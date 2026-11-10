"""HTTP layer for yemek_com_mcp.

yemek.com serves its pages server-rendered with no login and no API
key. Search is a public JSON endpoint the site's own search page
calls (``/ara/sonuclar/?q=...&rows=...``) — no key, no session.
Transport uses curl-cffi chrome120 impersonation (the proven
Turkey-factory pattern) with a plain-requests fallback, so one
transport failing does not break the server. Requests are kept
gentle (one at a time, ~0.8s apart) and read-only.
"""
from __future__ import annotations

import time
from urllib.parse import quote

from curl_cffi import requests as _creq
import requests as _plain

BASE = "https://yemek.com"
TIMEOUT = 30.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_last_fetch = 0.0


class YemekError(RuntimeError):
    pass


def _throttle() -> None:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    _last_fetch = time.monotonic()


_PROFILES = ("chrome120", "chrome131", "safari17_0")
_MAX_ATTEMPTS = 2  # one retry with the next profile
_RETRY_BACKOFF = 1.0  # seconds between attempts
_profile_idx = 0  # sticky: profile that last succeeded


def _request(url: str, headers: dict, timeout: float = TIMEOUT):
    """GET with fingerprint rotation.

    Starts at the sticky profile (chrome120 on a fresh process), retries
    once with the next profile on HTTP 403/429 or a transport error, then
    returns the last response (so the caller raises the specific 403/429
    error) or raises a network error if every attempt failed at the
    transport. Added 2026-11-10 (fleet audit fix).
    """
    global _profile_idx
    last_exc: Exception | None = None
    for k in range(_MAX_ATTEMPTS):
        profile = _PROFILES[(_profile_idx + k) % len(_PROFILES)]
        try:
            resp = _creq.get(url, impersonate=profile, headers=headers, timeout=timeout)
        except Exception as e:
            last_exc = e
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            raise YemekError(f"network error fetching {url}: {e}") from e
        if resp.status_code in (403, 429):
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            return resp
        _profile_idx = (_profile_idx + k) % len(_PROFILES)
        return resp
    raise YemekError(f"network error fetching {url}: {last_exc}") from last_exc


def _get(url: str, accept_json: bool = False) -> str:
    _throttle()
    headers = dict(_HEADERS)
    if accept_json:
        headers["Accept"] = "application/json, text/plain, */*"
    try:
        resp = _request(url, headers)
        status, text = resp.status_code, resp.text
    except Exception:
        # Fallback transport: plain requests with a browser UA.
        try:
            resp = _plain.get(url, headers={**headers, "User-Agent": _UA}, timeout=TIMEOUT)
            status, text = resp.status_code, resp.text
        except YemekError:
            raise
        except Exception as e:
            raise YemekError(f"network error fetching {url}: {e}") from e
    if status == 403:
        raise YemekError("yemek.com refused the request (HTTP 403, bot wall) — try again later")
    if status == 429:
        raise YemekError("yemek.com rate-limited the request (HTTP 429) — try again later")
    if status == 404:
        raise YemekError(f"yemek.com has no page at {url} (HTTP 404)")
    if status != 200:
        raise YemekError(f"yemek.com returned HTTP {status} for {url}")
    return text


def fetch_search_json(query: str, rows: int = 12, recipes_start: int = 0, posts_start: int = 0) -> str:
    """Public search JSON: /ara/sonuclar/?q=<query>&rows=<n>.
    Recipes come back 3 per page — paginate with recipes_start."""
    url = (
        f"{BASE}/ara/sonuclar/?q={quote(query)}&rows={rows}"
        f"&recipes_start={recipes_start}&posts_start={posts_start}"
    )
    return _get(url, accept_json=True)


def fetch_recipe_page(slug: str) -> str:
    return _get(f"{BASE}/tarif/{slug}/")


def fetch_home() -> str:
    return _get(f"{BASE}/")


def fetch_bugun() -> str:
    return _get(f"{BASE}/bugun-ne-pisirsem/")


def fetch_tarif_list(query: str | None = None) -> str:
    """Server-rendered /tarif/ listing, optionally filtered by ?q=."""
    url = f"{BASE}/tarif/"
    if query:
        url += f"?q={quote(query)}"
    return _get(url)


def health_check() -> dict:
    """One polite probe of the source site.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `yemek_health` tool
    and the daily smoke CI. Added 2026-11-10 (fleet audit fix).
    """
    url = "https://yemek.com/"
    try:
        fetch_home()
    except YemekError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
