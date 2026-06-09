"""Guest voting — fingerprint-based, one vote per guest per song."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_party
from app.lib.fingerprint import make_fingerprint
from app.models import Party, Song, Vote
from app.schemas import VoteRead
from app.services.queue import recount_votes
from app.services.websocket import manager

router = APIRouter(prefix="/party/{code}/songs/{song_id}/vote", tags=["votes"])


def _get_song(session: Session, party: Party, song_id: str) -> Song:
    song = session.get(Song, song_id)
    if not song or song.party_id != party.id:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.post("", response_model=VoteRead, status_code=201)
async def vote(
    song_id: str,
    request: Request,
    party: Party = Depends(get_party),
    session: Session = Depends(get_session),
):
    song = _get_song(session, party, song_id)
    fingerprint = make_fingerprint(request)
    session.add(Vote(song_id=song.id, guest_fingerprint=fingerprint))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Already voted for this song")

    count = recount_votes(session, song)
    await manager.broadcast(
        party.code, "vote_updated", {"song_id": song.id, "vote_count": count}
    )
    return VoteRead(song_id=song.id, vote_count=count, voted=True)


@router.delete("", response_model=VoteRead)
async def unvote(
    song_id: str,
    request: Request,
    party: Party = Depends(get_party),
    session: Session = Depends(get_session),
):
    song = _get_song(session, party, song_id)
    fingerprint = make_fingerprint(request)
    existing = session.exec(
        select(Vote).where(
            Vote.song_id == song.id, Vote.guest_fingerprint == fingerprint
        )
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="No vote to withdraw")
    session.delete(existing)
    session.commit()

    count = recount_votes(session, song)
    await manager.broadcast(
        party.code, "vote_updated", {"song_id": song.id, "vote_count": count}
    )
    return VoteRead(song_id=song.id, vote_count=count, voted=False)
