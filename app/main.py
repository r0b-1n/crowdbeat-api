"""FastAPI application entrypoint.

Registers CORS middleware and routers. Routers are added incrementally as the
backend is built out (auth, party, songs, votes, search, ws).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="CrowdBeat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://crowdbeat.app",
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,  # wichtig für Cookies
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Router registration (added in later steps):
# app.include_router(auth.router)
# app.include_router(party.router)
# app.include_router(songs.router)
# app.include_router(votes.router)
# app.include_router(search.router)
# app.include_router(ws.router)
