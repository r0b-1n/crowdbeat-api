# crowdbeat-api

REST API + WebSocket backend for **CrowdBeat** — a party song-voting app with
Spotify integration. Built with **FastAPI** + **SQLModel** + **Alembic**.

See [`PLANNING_API.md`](./PLANNING_API.md) for the full design and the 10-step
build roadmap. This repository currently implements **steps 1–2** (project
setup + models + initial migration).

## Tech stack

| Area | Technology |
|---|---|
| Framework | FastAPI |
| Database | SQLite via SQLModel (SQLAlchemy + Pydantic) |
| Migrations | Alembic |
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
# edit .env — set SECRET_KEY and (later) Spotify credentials

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
- `FRONTEND_URL` — allowed CORS origin / OAuth redirect target
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` / `SPOTIFY_REDIRECT_URI` — needed
  once the auth router (step 3) is in place
