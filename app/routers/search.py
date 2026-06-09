"""Track search, proxied to the keyless Deezer API."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_party
from app.models import Party
from app.schemas import SearchResult
from app.services import deezer

router = APIRouter(prefix="/party/{code}/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(min_length=1, max_length=200),
    party: Party = Depends(get_party),
):
    if party.status == "ended":
        raise HTTPException(status_code=409, detail="Party has ended")
    try:
        return await deezer.search_tracks(q)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Search provider unavailable")
