"""Party CRUD + QR code."""

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.dependencies import get_party, require_host, require_party_host
from app.lib.qr import make_qr_png
from app.models import HostSession, Party
from app.schemas import PartyCreate, PartyRead, PartyUpdate
from app.services.party import create_party
from app.services.websocket import manager

router = APIRouter(prefix="/party", tags=["party"])


@router.post("", response_model=PartyRead, status_code=201)
async def create(
    body: PartyCreate,
    host: HostSession = Depends(require_host),
    session: Session = Depends(get_session),
):
    return create_party(session, host, body.name)


@router.get("/{code}", response_model=PartyRead)
async def read(party: Party = Depends(get_party)):
    return party


@router.patch("/{code}", response_model=PartyRead)
async def update(
    body: PartyUpdate,
    party: Party = Depends(require_party_host),
    session: Session = Depends(get_session),
):
    if body.name is not None:
        party.name = body.name
    if body.status is not None:
        party.status = body.status
    session.add(party)
    session.commit()
    session.refresh(party)
    if body.status == "ended":
        await manager.broadcast(party.code, "party_ended", {})
    return party


@router.delete("/{code}", status_code=204)
async def end(
    party: Party = Depends(require_party_host),
    session: Session = Depends(get_session),
):
    party.status = "ended"
    session.add(party)
    session.commit()
    await manager.broadcast(party.code, "party_ended", {})


@router.get("/{code}/qr")
async def qr(party: Party = Depends(require_party_host)):
    join_url = f"{settings.FRONTEND_URL}/party/{party.code}"
    return Response(content=make_qr_png(join_url), media_type="image/png")
