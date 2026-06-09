"""Queue helpers: sorting and song status transitions."""

from sqlmodel import Session, func, select

from app.models import Song, Vote

# pending -> approved | rejected; approved -> played. Everything else is invalid.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected"},
    "approved": {"played", "rejected"},
    "rejected": set(),
    "played": set(),
}


def approved_songs_sorted(session: Session, party_id: str) -> list[Song]:
    return list(
        session.exec(
            select(Song)
            .where(Song.party_id == party_id, Song.status == "approved")
            .order_by(Song.vote_count.desc(), Song.added_at.asc())
        )
    )


def pending_songs(session: Session, party_id: str) -> list[Song]:
    return list(
        session.exec(
            select(Song)
            .where(Song.party_id == party_id, Song.status == "pending")
            .order_by(Song.added_at.asc())
        )
    )


def can_transition(current: str, new: str) -> bool:
    return new in VALID_TRANSITIONS.get(current, set())


def recount_votes(session: Session, song: Song) -> int:
    count = session.exec(
        select(func.count()).select_from(Vote).where(Vote.song_id == song.id)
    ).one()
    song.vote_count = int(count)
    session.add(song)
    session.commit()
    session.refresh(song)
    return song.vote_count
