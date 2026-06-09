"""Host auth: anonymous signed sessions, no OAuth."""

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.dependencies import SESSION_COOKIE, require_host, sign_session_id
from app.models import HostSession
from app.schemas import HostRead, SessionCreate

router = APIRouter(prefix="/auth", tags=["auth"])

# Secure cookies only make sense once the app is served over HTTPS.
_COOKIE_SECURE = settings.FRONTEND_URL.startswith("https")


def set_session_cookie(response: Response, host_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        sign_session_id(host_id),
        httponly=True,
        samesite="lax",
        secure=_COOKIE_SECURE,
        max_age=60 * 60 * 24 * 7,
    )


@router.post("/session", response_model=HostRead, status_code=201)
async def create_session(
    body: SessionCreate | None = None,
    response: Response = None,
    session: Session = Depends(get_session),
):
    host = HostSession(display_name=body.display_name if body else None)
    session.add(host)
    session.commit()
    session.refresh(host)
    set_session_cookie(response, host.id)
    return host


@router.get("/me", response_model=HostRead)
async def me(host: HostSession = Depends(require_host)):
    return host


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    host: HostSession = Depends(require_host),
    session: Session = Depends(get_session),
):
    session.delete(host)
    session.commit()
    response.delete_cookie(SESSION_COOKIE)
