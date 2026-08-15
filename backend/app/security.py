"""Ed25519-signed JWTs for session tokens and receipts (PRD non-goal 3: signed JWTs
with a keypair, not a custom cert authority / full X.509 PKI).

AgentMart (the issuer) holds one Ed25519 keypair (see scripts/generate_issuer_keypair.py)
and signs every session token/receipt with the private key; verification only needs the
public key. Revocation is a live per-agent flag (Agent.key_active, checked in deps.py),
not certificate expiry/CRL.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization

from app.config import ISSUER_PRIVATE_KEY_PATH, ISSUER_PUBLIC_KEY_PATH, JWT_ALGORITHM


def _load_private_key():
    with open(ISSUER_PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def _load_public_key():
    with open(ISSUER_PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


ISSUER_PRIVATE_KEY = _load_private_key()
ISSUER_PUBLIC_KEY = _load_public_key()


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
    return jwt.encode(payload, ISSUER_PRIVATE_KEY, algorithm=JWT_ALGORITHM)


def decode_session_claims(token: str) -> dict[str, Any]:
    """Returns the full token payload (agent_id, mandate, trust snapshot), raises
    jwt.PyJWTError if invalid/expired. Signature-valid does not imply still-authorised —
    callers must also check Agent.key_active (deps.get_agent_session does)."""
    return jwt.decode(token, ISSUER_PUBLIC_KEY, algorithms=[JWT_ALGORITHM])


def sign_receipt(payload: dict[str, Any]) -> str:
    body = {**payload, "iat": datetime.now(timezone.utc)}
    return jwt.encode(body, ISSUER_PRIVATE_KEY, algorithm=JWT_ALGORITHM)


def verify_receipt(token: str) -> dict[str, Any]:
    return jwt.decode(token, ISSUER_PUBLIC_KEY, algorithms=[JWT_ALGORITHM])
