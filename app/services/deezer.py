"""Deezer track search — keyless public API, proxied by the backend.

Deezer allows ~50 requests / 5 s per IP, so identical queries are cached
in-memory for a short TTL.
"""

import time

import httpx

DEEZER_SEARCH_URL = "https://api.deezer.com/search"
CACHE_TTL_SECONDS = 60
_cache: dict[str, tuple[float, list[dict]]] = {}


def _map_track(item: dict) -> dict:
    return {
        "track_id": str(item["id"]),
        "title": item.get("title", ""),
        "artist": (item.get("artist") or {}).get("name", ""),
        "album_art_url": (item.get("album") or {}).get("cover_medium") or "",
        "duration_ms": int(item.get("duration", 0)) * 1000,
        "preview_url": item.get("preview") or None,
    }


async def search_tracks(query: str, limit: int = 10) -> list[dict]:
    key = f"{query.strip().lower()}:{limit}"
    cached = _cache.get(key)
    now = time.monotonic()
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            DEEZER_SEARCH_URL, params={"q": query, "limit": limit}
        )
        resp.raise_for_status()
        payload = resp.json()

    results = [_map_track(item) for item in payload.get("data", [])]
    _cache[key] = (now, results)
    return results
