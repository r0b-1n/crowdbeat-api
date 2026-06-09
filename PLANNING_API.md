# CrowdBeat — Backend Planning (API)

> **Rev. 2 (Juni 2026):** Spotify-Integration ersetzt durch YouTube-Player +
> Deezer-Suche. Spotify hat im Februar 2026 den Development Mode hinter einen
> Premium-Zwang gestellt (1 Client ID, 5 Testnutzer, reduziertes Endpoint-Set)
> — ohne Premium-Account ist der ursprüngliche Plan nicht umsetzbar.
> Siehe Abschnitt „Pivot: Warum kein Spotify mehr".

## Überblick

REST API + WebSocket Backend für CrowdBeat.
Gebaut mit **Python + FastAPI**, Datenbank **SQLite** (Phase 1), später PostgreSQL + Redis.

Dieses Repo: `crowdbeat-api` — separates Repo vom Frontend (`crowdbeat-ui`).

**Kern-Erfahrung:** Host erstellt eine Party, Gäste treten per QR-Code bei,
schlagen Songs vor und voten — die gevotete Queue wird **automatisch im
Host-Dashboard abgespielt** (eingebetteter YouTube-Player). Gäste brauchen
keinen Account, der Host auch nicht.

---

## Pivot: Warum kein Spotify mehr

Die Spotify-Änderungen vom 06.02.2026 (wirksam ab 11.02. für neue, 09.03. für
bestehende Apps) machen den ursprünglichen Plan unbrauchbar:

- Development Mode erfordert einen **Spotify-Premium-Account**
- Nur noch 1 Client ID pro Developer, max. 5 autorisierte Nutzer
- Reduziertes Endpoint-Set; Extended Quota nur für verifizierte Unternehmen

**Ersatzarchitektur (Variante 1):**

| Funktion | Vorher (Spotify) | Jetzt |
|---|---|---|
| Song-Suche | Web API via Host-Token | **Deezer API** (keyless, ohne Registrierung) |
| Wiedergabe | Playlist im Spotify-Account des Hosts | **YouTube IFrame Player** im Host-Dashboard |
| Track→Video | — | **YouTube Data API v3** beim Approve (kostenloser Key, optional) |
| Host-Login | OAuth/PKCE | Simple signierte Session (kein OAuth) |

Damit bleibt die Kern-Erfahrung erhalten: Gäste voten, die Musik folgt
automatisch der Queue — nur die Quelle ist YouTube statt Spotify.

---

## Tech Stack

| Bereich | Technologie |
|---|---|
| Framework | FastAPI |
| Datenbank | SQLite via SQLModel (SQLAlchemy + Pydantic) |
| Migrations | Alembic |
| WebSockets | FastAPI native WebSockets |
| Auth/Sessions | itsdangerous (signed session cookies) |
| Song-Suche | Deezer API via httpx (keyless) |
| Track→Video-Auflösung | YouTube Data API v3 via httpx (optionaler API-Key) |
| Wiedergabe | YouTube IFrame Player API (reines Frontend, kein Key) |
| QR Code | qrcode[pil] |
| Dev Server | uvicorn |
| Env | python-dotenv / pydantic-settings |
| Testing | pytest + httpx (AsyncClient) |

---

## Projektstruktur

```
crowdbeat-api/
├── app/
│   ├── main.py               # FastAPI App, CORS, Router-Registrierung
│   ├── config.py             # Settings aus .env (pydantic-settings)
│   ├── database.py           # SQLite Engine + Session Dependency
│   ├── models.py             # SQLModel Table-Definitionen
│   ├── schemas.py            # Pydantic Request/Response Schemas
│   ├── dependencies.py       # get_session, require_host (Auth-Guard)
│   ├── routers/
│   │   ├── auth.py           # /auth/session, /auth/me, /auth/logout
│   │   ├── party.py          # /party CRUD + QR
│   │   ├── songs.py          # /party/{code}/songs
│   │   ├── votes.py          # /party/{code}/songs/{id}/vote
│   │   ├── search.py         # /party/{code}/search (Deezer)
│   │   └── ws.py             # /ws/{code} WebSocket
│   ├── services/
│   │   ├── deezer.py         # Deezer-Suche (httpx, keyless)
│   │   ├── youtube.py        # Track→Video-Auflösung (Data API v3)
│   │   ├── party.py          # Business Logic: Party erstellen, beenden
│   │   ├── queue.py          # Queue-Sortierung, Song-Status-Übergänge
│   │   └── websocket.py      # Connection Manager (broadcast)
│   └── lib/
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
    id:           str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    display_name: str | None = None
    created_at:   datetime = Field(default_factory=datetime.utcnow)

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
    track_id:         str                       # Deezer Track-ID
    title:            str
    artist:           str
    album_art_url:    str
    duration_ms:      int
    preview_url:      str | None = None         # 30s-MP3 von Deezer
    youtube_video_id: str | None = None         # wird beim Approve aufgelöst
    added_by_name:    str
    status:           str = Field(default="pending")  # pending|approved|rejected|played
    vote_count:       int = Field(default=0)
    added_at:         datetime = Field(default_factory=datetime.utcnow)

class Vote(SQLModel, table=True):
    # Unique-Constraint (song_id, guest_fingerprint) gegen Mehrfach-Votes
    id:                str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    song_id:           str = Field(foreign_key="song.id")
    guest_fingerprint: str
    voted_at:          datetime = Field(default_factory=datetime.utcnow)
```

---

## API Endpoints

### Auth (`/auth`)

Kein OAuth — der Host bekommt eine anonyme, signierte Session.

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| POST | `/auth/session` | — | HostSession erstellen, signierten Cookie setzen |
| GET | `/auth/me` | Host | Aktuelle Session zurückgeben |
| POST | `/auth/logout` | Host | Session löschen, Cookie entfernen |

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

**Approve-Hook:** Wechselt der Status auf `approved`, löst das Backend via
`services/youtube.py` die Suche `"{artist} {title}"` zu einer
`youtube_video_id` auf (YouTube Data API, `type=video`, `videoCategoryId=10`)
und speichert sie am Song. Ohne konfigurierten `YOUTUBE_API_KEY` oder ohne
Treffer bleibt das Feld `NULL` — das Frontend zeigt dann einen
YouTube-Suchlink statt Auto-Play (Graceful Degradation).

### Votes (`/party/{code}/songs/{id}/vote`)

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| POST | `/party/{code}/songs/{id}/vote` | Public | Vote abgeben (Fingerprint-Check) |
| DELETE | `/party/{code}/songs/{id}/vote` | Public | Vote zurückziehen |

### Search

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| GET | `/party/{code}/search?q=` | Public | Deezer-Suche, vom Backend proxied |

Response-Items: `{track_id, title, artist, album_art_url, duration_ms, preview_url}`
— gemappt aus Deezer `data[]` (`id`, `title`, `artist.name`,
`album.cover_medium`, `duration * 1000`, `preview`).

Deezer: `GET https://api.deezer.com/search?q={query}&limit=10` — kein API-Key,
keine Registrierung. Rate-Limit ~50 Requests / 5 s pro IP → Backend cached
identische Queries kurz (in-memory, TTL ~60 s).

### WebSocket

| Path | Beschreibung |
|---|---|
| `WS /ws/{code}` | Live-Updates für alle Verbindungen einer Party |

---

## WebSocket Events

Der Server broadcastet JSON-Events an alle verbundenen Clients einer Party:

```json
{ "event": "song_added",    "data": { ...Song } }
{ "event": "song_approved", "data": { "song_id": "...", "youtube_video_id": "..." } }
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
- Kein OAuth, keine Tokens, kein Refresh — `POST /auth/session` legt die
  Session an, fertig. Wer den Cookie hat, ist der Host seiner Parties.

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

## Host-Player (Frontend, `crowdbeat-ui`)

Das Host-Dashboard **ist** der Player: eine `YouTubePlayer`-Komponente
(YouTube IFrame Player API) spielt die gevotete Queue automatisch ab.

```
1. Dashboard lädt approved Songs (sortiert nach vote_count DESC)
2. Player lädt youtube_video_id des obersten Songs → spielt ab
3. onStateChange === ENDED
   → PATCH /party/{code}/songs/{id}  { status: "played" }
   → nächster Song aus der (live per WS aktualisierten) Queue
4. Play/Pause/Skip-Buttons im Dashboard steuern den Player direkt
```

**Bekannte Einschränkungen + Fallbacks:**

- **Label-gesperrte Embeds**: Manche Musikvideos sind nicht einbettbar
  (`onError` 101/150) → Frontend überspringt zum nächsten Song und zeigt
  einen „auf YouTube öffnen"-Link für den gesperrten Track.
- **Autoplay-Block**: Browser blockieren Autoplay ohne User-Interaktion
  (`onAutoplayBlocked`-Event) → Host startet die Wiedergabe einmal manuell,
  danach läuft die Queue durch.
- **Referer**: YouTube verlangt einen HTTP-Referer-Header — keine
  `no-referrer`-Policy auf der Dashboard-Seite setzen.
- **Werbung**: ohne YouTube Premium läuft ggf. Werbung zwischen Videos.
- `youtube_video_id === null` (kein Key / kein Treffer) → Karte zeigt
  YouTube-Suchlink, Player überspringt den Song.

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
# App
SECRET_KEY=change-me-in-production
FRONTEND_URL=http://localhost:5173
DATABASE_URL=sqlite:///./crowdbeat.db

# YouTube Data API v3 (optional — ohne Key keine Auto-Aufloesung beim Approve)
YOUTUBE_API_KEY=

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

Zusätzlich: `spotifyTrackId` in den Frontend-Typen wird zu `trackId`;
der Mock-„Spotify verbinden"-Button auf der HostSetupPage entfällt
(ersetzt durch implizites `POST /auth/session` beim Party-Erstellen).

### WebSocket Hook (`src/hooks/usePartySocket.ts`)

```typescript
export function usePartySocket(code: string) {
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/${code}`);
    ws.onmessage = (e) => {
      const { event, data } = JSON.parse(e.data);
      if (event === 'vote_updated')  store.updateVoteCount(data.song_id, data.vote_count);
      if (event === 'song_added')    store.addSong(data);
      if (event === 'song_approved') store.approveSong(data.song_id, data.youtube_video_id);
      // ...
    };
    return () => ws.close();
  }, [code]);
}
```

### Neu: `YouTubePlayer`-Komponente (Host-Dashboard)

Siehe Abschnitt „Host-Player" — IFrame Player API laden, Queue abspielen,
ENDED → `played` patchen, Fehler 101/150 → Skip + Link.

### `.env` im Frontend ergänzen

```env
VITE_API_URL=http://localhost:8000
```

---

## Implementierungs-Reihenfolge für Claude Code

1. ✅ **Projekt-Setup** — FastAPI + SQLModel + Alembic + uvicorn, `main.py` + `database.py` + `.env`
2. ✅ **Models + Migration** — alle SQLModel-Tabellen, Alembic-Migrationen
   (inkl. Pivot-Migration: Spotify-Felder raus, `youtube_video_id`/`preview_url` rein)
3. ✅ **Auth Router** — `POST /auth/session` + `GET /auth/me` + `POST /auth/logout` + signierter Cookie
4. ✅ **Party Router** — CRUD, Code-Generator (`XK4-92B`-Format, kollisionssicher)
5. ✅ **Songs Router** — add, list (approved/played), status-update mit Übergangs-Validierung, delete
6. ✅ **Votes Router** — vote/unvote mit Fingerprint-Unique-Check
7. ✅ **Search Router** — Deezer-Suche (keyless) + `services/youtube.py` Resolver für den Approve-Hook
8. ✅ **WebSocket** — Connection Manager + broadcast in allen Song/Vote-Endpoints
9. ✅ **QR Endpoint** — `/party/{code}/qr` als PNG
10. ✅ **Frontend-Integration** — `src/api/client.ts` + alle `src/api/*.ts` umgestellt + WebSocket-Hook + **YouTubePlayer-Komponente** (in `crowdbeat-ui`)

---

## YouTube Data API Key einrichten (optional, einmalig manuell)

Nur nötig für die automatische Track→Video-Auflösung beim Approve.
Kostenlos, kein Abo, keine Zahlungsdaten:

1. https://console.cloud.google.com → Projekt erstellen
2. „YouTube Data API v3" aktivieren
3. API-Key erstellen (Credentials → API Key) und in `.env` als `YOUTUBE_API_KEY` eintragen

Quota: 10.000 Units/Tag, eine Suche kostet 100 Units → ~100 Song-Approves/Tag.
Reicht für den Hobby-Betrieb; ohne Key funktioniert alles außer Auto-Play
(Songs zeigen dann einen YouTube-Suchlink).

---

## Was in Phase 2 kommt (nicht jetzt)

- PostgreSQL statt SQLite
- Redis für WebSocket-State (Multi-Instance)
- Rate Limiting (slowapi)
- Alternative Player-Quellen (z.B. Deezer-Preview-Modus als reiner 30s-Player)
- Deployment (Railway / Fly.io)
