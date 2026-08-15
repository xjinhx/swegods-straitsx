from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException
from sqlmodel import Session, select

from app.config import MERCHANT_API_KEY
from app.models import Agent, AuditEvent, Order
from app.schemas import Mandate
from app.security import decode_session_claims


@dataclass
class AgentSession:
    """An authenticated request's agent identity, plus the mandate and identity/mandate
    scores that were frozen into the session token at /identify time — not the agent's
    current (possibly since-changed) values, so a token can't inherit a mandate it
    was never issued under.

    identity_score and mandate_scope_score stay frozen (trust-score-v2): they
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
    if not agent.key_active:
        raise HTTPException(status_code=403, detail="agent credential has been revoked")

    trust = claims["trust"]
    return AgentSession(
        agent=agent,
        mandate=Mandate(**claims["mandate"]),
        identity_score=trust["identity_score"],
        mandate_scope_score=trust["mandate_scope_score"],
        trust_score=trust["trust_score"],
    )


def require_merchant_auth(x_merchant_key: str | None = Header(default=None)) -> None:
    """Gate for the merchant's own dashboard endpoints (/merchant/*: revoke, override,
    rule builder) — distinct from agent-facing trust scoring, which stays open on
    purpose at /identify (the score is the gate, not a login wall). This is the
    merchant's control panel, which does need one.

    MERCHANT_API_KEY unset means the gate is off, matching behavior before it existed,
    so existing deployments aren't broken until they opt in by setting it.
    """
    if not MERCHANT_API_KEY:
        return
    if x_merchant_key != MERCHANT_API_KEY:
        raise HTTPException(status_code=401, detail="missing or invalid X-Merchant-Key header")


def agent_order_history(session: Session, agent_id: str) -> tuple[int, int]:
    """(successes, total) over this agent's *completed* orders only, for
    trust.score_reputation — see the comment above REPUTATION_Z in trust.py for why
    "blocked" and "failed" orders are excluded entirely rather than counted as
    failures. Within completed orders, one that needed a merchant override to get past
    /checkout in the first place counts toward `total` but not `successes` — the
    override is the one real labeled "this wasn't actually trustworthy" signal this
    system has.

    Queried fresh on every call (not cached on the Agent row) so an order resolved
    earlier in the *same* session already counts by the next stage.
    """
    completed_order_ids = session.exec(
        select(Order.order_id).where(Order.agent_id == agent_id, Order.status == "completed")
    ).all()
    total = len(completed_order_ids)
    if total == 0:
        return 0, 0

    overridden_order_ids = set(session.exec(
        select(AuditEvent.order_id).where(
            AuditEvent.order_id.in_(completed_order_ids), AuditEvent.step == "override"
        )
    ).all())
    successes = total - len(overridden_order_ids)
    return successes, total
