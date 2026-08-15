"""POST /identify.

Agent identity is derived from the credential itself (its hash), so repeat calls with
the same credential resolve to the same agent record instead of minting a new identity
every time — that's what lets us track identify velocity (a behavioural signal) per
agent.
"""
import hashlib
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.audit import log_event
from app.config import MERCHANT_NAME
from app.database import get_session
from app.models import Agent
from app.schemas import IdentifyRequest, IdentifyResponse, TrustBreakdown
from app.security import issue_session_token
from app.trust import IDENTIFY_VELOCITY_WINDOW, compute_trust_score

router = APIRouter(tags=["identity"])


@router.post("/identify", response_model=IdentifyResponse)
def identify(payload: IdentifyRequest, session: Session = Depends(get_session)):
    agent_id = "agt_" + hashlib.sha256(payload.credential.encode()).hexdigest()[:16]
    now = datetime.utcnow()

    agent = session.get(Agent, agent_id)
    if agent and (now - agent.last_identify_at) <= IDENTIFY_VELOCITY_WINDOW:
        identify_count_in_window = agent.identify_count + 1
    else:
        identify_count_in_window = 1

    breakdown = compute_trust_score(
        mandate=payload.mandate,
        credential=payload.credential,
        issuer=payload.issuer,
        identify_count_in_window=identify_count_in_window,
    )
    session_token = issue_session_token(
        agent_id,
        mandate=payload.mandate.model_dump(),
        trust=breakdown,
        expiry_hours=payload.mandate.expiry_hours,
    )
    credential_valid = breakdown["identity_score"] > 20

    if agent is None:
        agent = Agent(agent_id=agent_id, name=payload.agent_name, created_at=now)

    agent.name = payload.agent_name
    agent.session_token = session_token
    agent.spend_cap_sgd = payload.mandate.spend_cap_sgd
    agent.merchant_whitelist_json = json.dumps(payload.mandate.merchant_whitelist)
    agent.expiry_hours = payload.mandate.expiry_hours
    agent.credential_issuer = payload.issuer
    agent.credential_valid = credential_valid
    agent.mandate_scope_score = breakdown["mandate_scope_score"]
    agent.identity_score = breakdown["identity_score"]
    agent.behavior_score = breakdown["behavior_score"]
    agent.trust_score = breakdown["trust_score"]
    agent.identify_count = identify_count_in_window
    agent.last_identify_at = now

    session.add(agent)
    session.commit()
    session.refresh(agent)

    log_event(
        session,
        step="identify",
        message=f'"{agent.name}" identified — trust score {agent.trust_score}',
        agent_id=agent_id,
        detail={
            "issuer": payload.issuer,
            "credential_valid": credential_valid,
            "identify_count_in_window": identify_count_in_window,
            **breakdown,
        },
    )

    return IdentifyResponse(
        agent_id=agent_id,
        session_token=session_token,
        merchant=MERCHANT_NAME,
        trust=TrustBreakdown(**breakdown),
    )
