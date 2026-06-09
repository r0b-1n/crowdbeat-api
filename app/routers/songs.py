"""Song suggestions, queue listing and host moderation."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.database import get_session
from app.dependencies import get_party, require_party_host
from app.models import Party, Song
from app.schemas import SongCreate, SongRead, SongUpdate
from app.services import queue, youtube
from app.services.websocket import manager

router = APIRouter(prefix="/party/{code}/songs", tags=["songs"])


def _get_song(session: Session, party: Party, song_id: str) -> Song:
    song = session.get(Song, song_id)
    if not song or song.party_id != party.id:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.get("", response_model=list[SongRead])
async def list_songs(
    status: str = Query(default="approved", pattern="^(approved|played)$"),
    party: Party = Depends(get_party),
    session: Session = Depends(get_session),
):
    return queue.songs_by_status(session, party.id, status)


@router.get("/pending", response_model=list[SongRead])
async def list_pending(
    party: Party = Depends(require_party_host),
    session: Session = Depends(get_session),
):
    return queue.pending_songs(session, party.id)


@router.post("", response_model=SongRead, status_code=201)
async def suggest(
    body: SongCreate,
    party: Party = Depends(get_party),
    session: Session = Depends(get_session),
):
    if party.status == "ended":
        raise HTTPException(status_code=409, detail="Party has ended")
    song = Song(party_id=party.id, **body.model_dump())
    session.add(song)
    session.commit()
    session.refresh(song)
    await manager.broadcast(party.code, "song_added", song.model_dump())
    return song


@router.patch("/{song_id}", response_model=SongRead)
async def update_status(
    song_id: str,
    body: SongUpdate,
    party: Party = Depends(require_party_host),
    session: Session = Depends(get_session),
):
    song = _get_song(session, party, song_id)
    if not queue.can_transition(song.status, body.status):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change status from '{song.status}' to '{body.status}'",
        )

    song.status = body.status
    if body.status == "approved" and not song.youtube_video_id:
        song.youtube_video_id = await youtube.resolve_video_id(song.artist, song.title)
    session.add(song)
    session.commit()
    session.refresh(song)

    if body.status == "approved":
        await manager.broadcast(
            party.code,
            "song_approved",
            {"song_id": song.id, "youtube_video_id": song.youtube_video_id},
        )
    elif body.status == "rejected":
        await manager.broadcast(party.code, "song_rejected", {"song_id": song.id})
    elif body.status == "played":
        await manager.broadcast(party.code, "song_played", {"song_id": song.id})
    return song


@router.delete("/{song_id}", status_code=204)
async def remove(
    song_id: str,
    party: Party = Depends(require_party_host),
    session: Session = Depends(get_session),
):
    song = _get_song(session, party, song_id)
    session.delete(song)
    session.commit()
    await manager.broadcast(party.code, "song_removed", {"song_id": song_id})
