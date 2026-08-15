import jwt
from fastapi import HTTPException
from sqlmodel import Session

from app.models import Agent
from app.security import decode_session_token


def get_agent_from_token(session: Session, token: str) -> Agent:
    try:
        agent_id = decode_session_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="session token expired, call /identify again")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid session token")

    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=401, detail="unknown agent")
    return agent
