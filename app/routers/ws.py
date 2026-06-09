"""WebSocket endpoint — live updates for all clients of a party."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.database import engine
from app.models import Party
from app.services.websocket import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/{code}")
async def party_socket(ws: WebSocket, code: str):
    with Session(engine) as session:
        party = session.exec(select(Party).where(Party.code == code)).first()
    if not party:
        await ws.close(code=4404, reason="Party not found")
        return

    await manager.connect(code, ws)
    try:
        # Clients only listen; we keep the connection open and ignore input.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(code, ws)
