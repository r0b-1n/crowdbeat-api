# crowdbeat-api

REST API + WebSocket backend for **CrowdBeat** — a party song-voting app where
guests suggest and vote on songs and the voted queue auto-plays in the host
dashboard via an embedded YouTube player. Built with **FastAPI** + **SQLModel**
+ **Alembic**. Song search is powered by the keyless Deezer API.

See [`PLANNING_API.md`](./PLANNING_API.md) for the full design and the 10-step
build roadmap. All backend steps (1–9) are implemented; the frontend
integration (step 10) lives in `crowdbeat-ui`.

## Tech stack

| Area | Technology |
|---|---|
| Framework | FastAPI |
| Database | SQLite via SQLModel (SQLAlchemy + Pydantic) |
| Migrations | Alembic |
| Song search | Deezer API (keyless, via httpx) |
| Track→video resolution | YouTube Data API v3 (optional free API key) |
| Playback | YouTube IFrame Player (frontend only) |
| Config | pydantic-settings / python-dotenv |
| Dev server | uvicorn |
| Testing | pytest |

## Project structure

```
crowdbeat-api/
├── app/
│   ├── main.py        # FastAPI app, CORS, /health, router registration
│   ├── config.py      # Settings loaded from .env
│   ├── database.py    # SQLite engine + get_session dependency
│   ├── models.py      # SQLModel table definitions
│   ├── routers/       # (added in later steps)
│   ├── services/      # (added in later steps)
│   └── lib/           # (added in later steps)
├── alembic/           # migration environment + versions/
├── tests/
├── .env.example
├── alembic.ini
└── requirements.txt
```

## Getting started

```bash
# 1. Create & activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# edit .env — set SECRET_KEY; YOUTUBE_API_KEY is optional

# 4. Create the database schema
alembic upgrade head

# 5. Run the dev server
uvicorn app.main:app --reload --port 8000
```

The API is then available at <http://localhost:8000>. A health check lives at
`GET /health`.

## Database migrations

After changing models in `app/models.py`:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

`alembic/env.py` reads `DATABASE_URL` from the app settings and uses
`SQLModel.metadata` for autogenerate, so migrations stay in sync with the models.

## Environment variables

See [`.env.example`](./.env.example). Key values:

- `SECRET_KEY` — signs session cookies (change in production)
- `DATABASE_URL` — defaults to `sqlite:///./crowdbeat.db`
- `FRONTEND_URL` — allowed CORS origin
- `YOUTUBE_API_KEY` — optional; enables automatic track→YouTube-video resolution
  when the host approves a song (see `PLANNING_API.md` for setup). Without it,
  approved songs simply carry no `youtube_video_id` and the frontend falls back
  to a YouTube search link.
