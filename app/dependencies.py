"""Shared FastAPI dependencies: DB session, host auth, party lookup."""

from fastapi import Depends, HTTPException, Request
from itsdangerous import BadSignature, URLSafeSerializer
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import HostSession, Party

SESSION_COOKIE = "session_id"

_serializer = URLSafeSerializer(settings.SECRET_KEY, salt="session-cookie")


def sign_session_id(host_id: str) -> str:
    return _serializer.dumps(host_id)


def verify_session_id(value: str) -> str | None:
    try:
        return _serializer.loads(value)
    except BadSignature:
        return None


async def require_host(
    request: Request, session: Session = Depends(get_session)
) -> HostSession:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    host_id = verify_session_id(cookie)
    if not host_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    host = session.get(HostSession, host_id)
    if not host:
        raise HTTPException(status_code=401, detail="Session expired")
    return host


async def get_party(code: str, session: Session = Depends(get_session)) -> Party:
    party = session.exec(select(Party).where(Party.code == code)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


async def require_party_host(
    party: Party = Depends(get_party), host: HostSession = Depends(require_host)
) -> Party:
    if party.host_session_id != host.id:
        raise HTTPException(status_code=403, detail="Not the host of this party")
    return party
