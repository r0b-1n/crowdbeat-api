"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


# --- Auth ---

class SessionCreate(BaseModel):
    display_name: str | None = None


class HostRead(BaseModel):
    id: str
    display_name: str | None
    created_at: datetime


# --- Party ---

class PartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PartyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, pattern="^(waiting|active|ended)$")


class PartyRead(BaseModel):
    id: str
    code: str
    name: str
    status: str
    created_at: datetime
    expires_at: datetime


# --- Songs ---

class SongCreate(BaseModel):
    track_id: str
    title: str = Field(min_length=1, max_length=200)
    artist: str = Field(min_length=1, max_length=200)
    album_art_url: str = ""
    duration_ms: int = Field(ge=0)
    preview_url: str | None = None
    added_by_name: str = Field(min_length=1, max_length=50)


class SongUpdate(BaseModel):
    status: str = Field(pattern="^(approved|rejected|played)$")


class SongRead(BaseModel):
    id: str
    party_id: str
    track_id: str
    title: str
    artist: str
    album_art_url: str
    duration_ms: int
    preview_url: str | None
    youtube_video_id: str | None
    added_by_name: str
    status: str
    vote_count: int
    added_at: datetime


# --- Votes ---

class VoteRead(BaseModel):
    song_id: str
    vote_count: int
    voted: bool


# --- Search ---

class SearchResult(BaseModel):
    track_id: str
    title: str
    artist: str
    album_art_url: str
    duration_ms: int
    preview_url: str | None
