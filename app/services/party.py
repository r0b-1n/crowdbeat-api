"""Party business logic: code generation and creation."""

import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models import HostSession, Party

# No ambiguous characters (0/O, 1/I/L) so codes stay easy to read out loud.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
PARTY_TTL_HOURS = 24


def generate_party_code(session: Session) -> str:
    while True:
        chars = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        code = f"{chars[:3]}-{chars[3:]}"  # z.B. "XK4-92B"-Format
        if not session.exec(select(Party).where(Party.code == code)).first():
            return code


def create_party(session: Session, host: HostSession, name: str) -> Party:
    party = Party(
        host_session_id=host.id,
        code=generate_party_code(session),
        name=name,
        status="waiting",
        expires_at=datetime.utcnow() + timedelta(hours=PARTY_TTL_HOURS),
    )
    session.add(party)
    session.commit()
    session.refresh(party)
    return party
