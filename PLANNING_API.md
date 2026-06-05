# CrowdBeat — Backend Planning (API)

## Überblick

REST API + WebSocket Backend für CrowdBeat.
Gebaut mit **Python + FastAPI**, Datenbank **SQLite** (Phase 1), später PostgreSQL + Redis.

Dieses Repo: `crowdbeat-api` — separates Repo vom Frontend (`crowdbeat-ui`).

---

## Tech Stack

| Bereich | Technologie |
|---|---|
| Framework | FastAPI |
| Datenbank | SQLite via SQLModel (SQLAlchemy + Pydantic) |
| Migrations | Alembic |
| WebSockets | FastAPI native WebSockets |
| Auth/Sessions | itsdangerous (signed session cookies) |
| Spotify OAuth | httpx (async HTTP client) |
| PKCE | hashlib + secrets (stdlib) |
| QR Code | qrcode[pil] |
| Dev Server | uvicorn |
| Env | python-dotenv |
| Testing | pytest + httpx (AsyncClient) |

---

## Projektstruktur

```
crowdbeat-api/
├── app/
│   ├── main.py               # FastAPI App, CORS, Router-Registrierung
│   ├── database.py           # SQLite Engine + Session Dependency
│   ├── models.py             # SQLModel Table-Definitionen
│   ├── schemas.py            # Pydantic Request/Response Schemas
│   ├── dependencies.py       # get_session, require_host (Auth-Guard)
│   ├── routers/
│   │   ├── auth.py           # /auth/login, /auth/callback, /auth/logout
│   │   ├── party.py          # /party CRUD
│   │   ├── songs.py          # /party/{code}/songs
│   │   ├── votes.py          # /party/{code}/songs/{id}/vote
│   │   ├── search.py         # /party/{code}/search
│   │   └── ws.py             # /ws/{code} WebSocket
│   ├── services/
│   │   ├── spotify.py        # Spotify API Wrapper (search, token refresh)
│   │   ├── party.py          # Business Logic: Party erstellen, beenden
│   │   ├── queue.py          # Queue-Sortierung, Song-Status-Übergänge
│   │   └── websocket.py      # Connection Manager (broadcast)
│   └── lib/
│       ├── pkce.py           # code_verifier + code_challenge generieren
│       ├── qr.py             # QR-Code PNG generieren
│       └── fingerprint.py    # Guest-Fingerprint aus IP + User-Agent
├── tests/
│   ├── test_party.py
│   ├── test_songs.py
│   └── test_votes.py
├── alembic/
│   └── versions/
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## Datenbank-Modelle (`app/models.py`)

SQLModel wird verwendet — kombiniert SQLAlchemy + Pydantic in einer Klasse.

```python
class HostSession(SQLModel, table=True):
    id:               str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    spotify_user_id:  str
    access_token:     str
    refresh_token:    str
    token_expires_at: datetime
    created_at:       datetime = Field(default_factory=datetime.utcnow)

class Party(SQLModel, table=True):
    id:              str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    host_session_id: str = Field(foreign_key="hostsession.id")
    code:            str = Field(unique=True)   # z.B. "XK4-92B"
    name:            str
    status:          str = Field(default="waiting")  # waiting | active | ended
    created_at:      datetime = Field(default_factory=datetime.utcnow)
    expires_at:      datetime

class Song(SQLModel, table=True):
    id:               str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    party_id:         str = Field(foreign_key="party.id")
    spotify_track_id: str
    title:            str
    artist:           str
    album_art_url:    str
    duration_ms:      int
    added_by_name:    str
    status:           str = Field(default="pending")  # pending|approved|rejected|played
    vote_count:       int = Field(default=0)
    added_at:         datetime = Field(default_factory=datetime.utcnow)

class Vote(SQLModel, table=True):
    id:               str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    song_id:          str = Field(foreign_key="song.id")
    guest_fingerprint: str
    voted_at:         datetime = Field(default_factory=datetime.utcnow)
```

---

## API Endpoints

### Auth (`/auth`)

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| GET | `/auth/login` | — | PKCE starten → Redirect zu Spotify |
| GET | `/auth/callback` | — | Code eintauschen, Session-Cookie setzen |
| POST | `/auth/logout` | Host | Session löschen |
| GET | `/auth/me` | Host | Aktuellen Host zurückgeben |

### Party (`/party`)

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| POST | `/party` | Host | Party erstellen → gibt `{id, code, name, status}` zurück |
| GET | `/party/{code}` | Public | Party-Info laden |
| PATCH | `/party/{code}` | Host | Name oder Status ändern |
| DELETE | `/party/{code}` | Host | Party beenden |
| GET | `/party/{code}/qr` | Host | QR-Code als PNG (image/png) |

### Songs (`/party/{code}/songs`)

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| GET | `/party/{code}/songs` | Public | Approved Songs, sortiert nach `vote_count DESC` |
| POST | `/party/{code}/songs` | Public | Song vorschlagen → Status `pending` |
| GET | `/party/{code}/songs/pending` | Host | Ausstehende Songs |
| PATCH | `/party/{code}/songs/{id}` | Host | Status ändern (approved/rejected/played) |
| DELETE | `/party/{code}/songs/{id}` | Host | Song entfernen |

### Votes (`/party/{code}/songs/{id}/vote`)

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| POST | `/party/{code}/songs/{id}/vote` | Public | Vote abgeben (Fingerprint-Check) |
| DELETE | `/party/{code}/songs/{id}/vote` | Public | Vote zurückziehen |

### Search

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| GET | `/party/{code}/search?q=` | Public | Spotify-Suche via Host-Token |

### WebSocket

| Path | Beschreibung |
|---|---|
| `WS /ws/{code}` | Live-Updates für alle Verbindungen einer Party |

---

## WebSocket Events

Der Server broadcastet JSON-Events an alle verbundenen Clients einer Party:

```json
{ "event": "song_added",    "data": { ...Song } }
{ "event": "song_approved", "data": { "song_id": "..." } }
{ "event": "song_rejected", "data": { "song_id": "..." } }
{ "event": "vote_updated",  "data": { "song_id": "...", "vote_count": 42 } }
{ "event": "song_played",   "data": { "song_id": "..." } }
{ "event": "song_removed",  "data": { "song_id": "..." } }
{ "event": "party_ended",   "data": {} }
```

### Connection Manager (`services/websocket.py`)

```python
class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, party_code: str, ws: WebSocket): ...
    def disconnect(self, party_code: str, ws: WebSocket): ...
    async def broadcast(self, party_code: str, event: str, data: dict): ...
```

Jeder API-Endpunkt der den State ändert (approve, vote, add song, ...) ruft danach `manager.broadcast()` auf.

---

## Auth & Session

- Host-Auth via **signed Cookie** (`session_id`) — signiert mit `SECRET_KEY` via `itsdangerous`
- Cookie: `HttpOnly=True`, `SameSite=Lax`, `Secure=True` (in Produktion)
- `HostSession` in SQLite gespeichert (kein Redis in Phase 1)
- Token-Refresh: vor jedem Spotify-API-Call prüfen ob `token_expires_at < now()` → refresh

### `require_host` Dependency

```python
async def require_host(request: Request, session: Session = Depends(get_session)) -> HostSession:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401)
    host = session.get(HostSession, verify_signature(session_id))
    if not host:
        raise HTTPException(401)
    return host
```

### Party-Ownership prüfen

```python
async def require_party_host(code: str, host: HostSession = Depends(require_host), ...):
    party = session.exec(select(Party).where(Party.code == code)).first()
    if not party or party.host_session_id != host.id:
        raise HTTPException(403)
    return party
```

---

## Spotify OAuth Flow (PKCE)

```
1. GET /auth/login
   → code_verifier generieren (secrets.token_urlsafe(64))
   → code_challenge = base64url(sha256(code_verifier))
   → state = secrets.token_urlsafe(16)
   → state + code_verifier in DB oder signed Cookie speichern (TTL 10min)
   → Redirect zu https://accounts.spotify.com/authorize?...

2. GET /auth/callback?code=...&state=...
   → state validieren
   → code_verifier laden
   → POST https://accounts.spotify.com/api/token (code + verifier)
   → access_token + refresh_token empfangen
   → HostSession in DB speichern
   → session_id Cookie setzen
   → Redirect zu {FRONTEND_URL}/host/{party_code} oder /create
```

### Benötigte Spotify Scopes

```
playlist-modify-public
playlist-modify-private
user-read-playback-state
user-modify-playback-state
```

---

## Guest Fingerprint (`lib/fingerprint.py`)

Kein Guest-Login — Identifikation über:

```python
def make_fingerprint(request: Request) -> str:
    ip = request.client.host
    ua = request.headers.get("user-agent", "")
    raw = f"{ip}:{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

Schutz gegen Mehrfach-Votes: `Vote`-Tabelle hat Unique-Constraint auf `(song_id, guest_fingerprint)`.

---

## CORS Konfiguration (`main.py`)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://crowdbeat.app"],
    allow_credentials=True,   # wichtig für Cookies
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## `.env.example`

```env
# Spotify
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://localhost:8000/auth/callback

# App
SECRET_KEY=change-me-in-production
FRONTEND_URL=http://localhost:5173
DATABASE_URL=sqlite:///./crowdbeat.db

# Optional (Phase 2)
# DATABASE_URL=postgresql://user:pass@localhost/crowdbeat
# REDIS_URL=redis://localhost:6379
```

---

## Frontend-Integration

Das Frontend (`crowdbeat-ui`) muss nach dieser Phase folgendes anpassen:

### `src/api/` — Mock → Real

Alle Funktionen in `src/api/` werden von Mock-Fixtures auf echte `fetch`-Calls umgestellt:

```typescript
// src/api/client.ts — gemeinsamer Basis-Client
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',   // Cookies mitsenden
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) throw new Error(`API Error ${res.status}`);
  return res.json();
}
```

```typescript
// src/api/party.ts
export const createParty = (name: string) =>
  apiFetch<Party>('/party', { method: 'POST', body: JSON.stringify({ name }) });

export const getParty = (code: string) =>
  apiFetch<Party>(`/party/${code}`);
```

### WebSocket Hook (`src/hooks/usePartySocket.ts`)

```typescript
export function usePartySocket(code: string) {
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${code}`);
    ws.onmessage = (e) => {
      const { event, data } = JSON.parse(e.data);
      // partyStore Actions dispatchen
      if (event === 'vote_updated') store.updateVoteCount(data.song_id, data.vote_count);
      if (event === 'song_added')   store.addSong(data);
      if (event === 'song_approved') store.approveSong(data.song_id);
      // ...
    };
    return () => ws.close();
  }, [code]);
}
```

### `.env` im Frontend ergänzen

```env
VITE_API_URL=http://localhost:8000
```

---

## Implementierungs-Reihenfolge für Claude Code

1. **Projekt-Setup** — FastAPI + SQLModel + Alembic + uvicorn installieren, `main.py` + `database.py` + `.env`
2. **Models + Migration** — alle SQLModel-Tabellen, erste Alembic-Migration ausführen
3. **Auth Router** — `/auth/login` + `/auth/callback` + PKCE + Session-Cookie
4. **Party Router** — CRUD, Code-Generator (`XK4-92B` Format: `secrets.token_urlsafe(4).upper()[:7]` mit Bindestrich)
5. **Songs Router** — add, list, status-update, delete
6. **Votes Router** — vote/unvote mit Fingerprint-Unique-Check
7. **Search Router** — Spotify-Suche via Host-Token + Auto-Refresh
8. **WebSocket** — Connection Manager + broadcast in alle Song/Vote-Endpoints einbauen
9. **QR Endpoint** — `/party/{code}/qr` als PNG
10. **Frontend-Integration** — `src/api/client.ts` + alle `src/api/*.ts` umstellen + WebSocket-Hook

---

## Spotify Developer App einrichten

Bevor Claude Code loslegt, muss einmalig manuell gemacht werden:

1. https://developer.spotify.com/dashboard → App erstellen
2. Redirect URI eintragen: `http://localhost:8000/auth/callback`
3. `Client ID` + `Client Secret` in `.env` eintragen

---

## Was in Phase 2 kommt (nicht jetzt)

- PostgreSQL statt SQLite
- Redis für WebSocket-State (Multi-Instance)
- Rate Limiting (slowapi)
- Spotify Playback-Control (aktuell nur Playlist)
- Deployment (Railway / Fly.io)
