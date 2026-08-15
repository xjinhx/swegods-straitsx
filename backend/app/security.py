"""Signed JWTs for session tokens and receipts (PRD non-goal 3: JWTs, not a custom
cert authority / full PKI)."""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import JWT_ALGORITHM, JWT_SECRET


def issue_session_token(agent_id: str, expiry_hours: float) -> str:
    payload = {
        "sub": agent_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> str:
    """Returns agent_id, raises jwt.PyJWTError if invalid/expired."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload["sub"]


def sign_receipt(payload: dict[str, Any]) -> str:
    body = {**payload, "iat": datetime.now(timezone.utc)}
    return jwt.encode(body, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_receipt(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
