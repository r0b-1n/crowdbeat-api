"""Track-to-video resolution via the YouTube Data API v3.

Called when the host approves a song. The API key is optional: without it (or
on any error / no hit) the function returns None and the frontend falls back
to a YouTube search link instead of auto-play.
"""

import logging

import httpx

from app.config import settings

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
MUSIC_CATEGORY_ID = "10"

logger = logging.getLogger(__name__)


async def resolve_video_id(artist: str, title: str) -> str | None:
    if not settings.YOUTUBE_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                YOUTUBE_SEARCH_URL,
                params={
                    "key": settings.YOUTUBE_API_KEY,
                    "q": f"{artist} {title}",
                    "part": "snippet",
                    "type": "video",
                    "videoCategoryId": MUSIC_CATEGORY_ID,
                    "maxResults": 1,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
    except Exception:
        logger.warning("YouTube resolution failed for %s - %s", artist, title, exc_info=True)
        return None
    if not items:
        return None
    return items[0].get("id", {}).get("videoId")
