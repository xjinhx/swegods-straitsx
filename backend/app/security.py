"""Signed JWTs for session tokens and receipts (PRD non-goal 3: JWTs, not a custom
cert authority / full PKI)."""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import JWT_ALGORITHM, JWT_SECRET


def issue_session_token(agent_id: str, mandate: dict[str, Any], trust: dict[str, Any], expiry_hours: float) -> str:
    """Freezes the mandate and trust breakdown in force at /identify time into the
    token itself, so a later /identify call with a different mandate can't silently
    change what an already-issued, still-valid token is authorised to do."""
    payload = {
        "sub": agent_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        "mandate": mandate,
        "trust": trust,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_session_claims(token: str) -> dict[str, Any]:
    """Returns the full token payload (agent_id, mandate, trust snapshot), raises
    jwt.PyJWTError if invalid/expired."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def sign_receipt(payload: dict[str, Any]) -> str:
    body = {**payload, "iat": datetime.now(timezone.utc)}
    return jwt.encode(body, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_receipt(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
