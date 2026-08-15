from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from sqlmodel import Session

from app.models import Agent
from app.schemas import Mandate
from app.security import decode_session_claims


@dataclass
class AgentSession:
    """An authenticated request's agent identity, plus the mandate and identity/mandate
    scores that were frozen into the session token at /identify time — not the agent's
    current (possibly since-changed) values, so a token can't inherit a mandate it
    was never issued under.

    identity_score and mandate_scope_score stay frozen (PRD-trust-score-v2): they
    answer "who is this agent", which shouldn't change mid-session. behavior_score is
    deliberately NOT exposed here — it's live now, read fresh off the Agent row by
    whoever needs it (checkout.py/authorise.py), not frozen into the token.
    """
    agent: Agent
    mandate: Mandate
    identity_score: float
    mandate_scope_score: float
    trust_score: float  # the identify-stage blend (identity+mandate only) — see trust.py


def get_agent_session(session: Session, token: str) -> AgentSession:
    try:
        claims = decode_session_claims(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="session token expired, call /identify again")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid session token")

    agent = session.get(Agent, claims["sub"])
    if not agent:
        raise HTTPException(status_code=401, detail="unknown agent")

    trust = claims["trust"]
    return AgentSession(
        agent=agent,
        mandate=Mandate(**claims["mandate"]),
        identity_score=trust["identity_score"],
        mandate_scope_score=trust["mandate_scope_score"],
        trust_score=trust["trust_score"],
    )
