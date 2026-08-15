from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from sqlmodel import Session

from app.models import Agent
from app.schemas import Mandate
from app.security import decode_session_claims


@dataclass
class AgentSession:
    """An authenticated request's agent identity, plus the mandate and trust score
    that were frozen into the session token at /identify time — not the agent's
    current (possibly since-changed) values, so a token can't inherit a mandate it
    was never issued under."""
    agent: Agent
    mandate: Mandate
    trust_score: float


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

    return AgentSession(
        agent=agent,
        mandate=Mandate(**claims["mandate"]),
        trust_score=claims["trust"]["trust_score"],
    )
