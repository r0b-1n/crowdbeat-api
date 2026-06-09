"""Guest fingerprinting — no guest login, identification via IP + User-Agent."""

import hashlib

from fastapi import Request


def make_fingerprint(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    raw = f"{ip}:{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
