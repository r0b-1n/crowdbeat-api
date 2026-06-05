"""SQLModel table definitions.

SQLModel combines SQLAlchemy + Pydantic in one class, so these double as the
ORM tables and the base for request/response schemas.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class HostSession(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    spotify_user_id: str
    access_token: str
    refresh_token: str
    token_expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Party(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    host_session_id: str = Field(foreign_key="hostsession.id")
    code: str = Field(unique=True, index=True)  # z.B. "XK4-92B"
    name: str
    status: str = Field(default="waiting")  # waiting | active | ended
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class Song(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    party_id: str = Field(foreign_key="party.id")
    spotify_track_id: str
    title: str
    artist: str
    album_art_url: str
    duration_ms: int
    added_by_name: str
    status: str = Field(default="pending")  # pending | approved | rejected | played
    vote_count: int = Field(default=0)
    added_at: datetime = Field(default_factory=datetime.utcnow)


class Vote(SQLModel, table=True):
    # One vote per guest fingerprint per song.
    __table_args__ = (
        UniqueConstraint("song_id", "guest_fingerprint", name="uq_vote_song_guest"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    song_id: str = Field(foreign_key="song.id")
    guest_fingerprint: str
    voted_at: datetime = Field(default_factory=datetime.utcnow)
