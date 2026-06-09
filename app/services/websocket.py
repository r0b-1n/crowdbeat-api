"""WebSocket connection manager — per-party broadcast of live events."""

import json

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, party_code: str, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.setdefault(party_code, []).append(ws)

    def disconnect(self, party_code: str, ws: WebSocket) -> None:
        conns = self.connections.get(party_code)
        if conns and ws in conns:
            conns.remove(ws)
        if conns is not None and not conns:
            del self.connections[party_code]

    async def broadcast(self, party_code: str, event: str, data: dict) -> None:
        message = json.dumps({"event": event, "data": data}, default=str)
        for ws in list(self.connections.get(party_code, [])):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(party_code, ws)


manager = ConnectionManager()
