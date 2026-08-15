"""POST /authorise — PRD Section 6 step 6. Charges via StraitsX's one-time card MCP
(mocked by default, see app/straitsx_client.py) and settles in XSGD.

PRD-trust-score-v2: StraitsX's settlement outcome now feeds payment_authority_score
into the blended live_trust_score instead of being a hard boolean disconnected from
trust. A StraitsXError still hard-fails the order (there's no card to charge without
StraitsX succeeding) but is now logged as a graded signal — see
trust.score_payment_authority for why that collapses to 2 outcomes rather than 4."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.audit import log_event
from app.database import get_session
from app.deps import get_agent_session
from app.models import Order
from app.schemas import AuthoriseRequest, AuthoriseResponse, ScoreBreakdown
from app.security import sign_receipt
from app.straitsx_client import StraitsXCardClient, StraitsXError
from app.trust import blend_authorise_score, score_payment_authority

router = APIRouter(tags=["authorise"])

ALLOWED_STATUSES = {"approved", "approved_override"}


@router.post("/authorise", response_model=AuthoriseResponse)
async def authorise(payload: AuthoriseRequest, session: Session = Depends(get_session)):
    agent_session = get_agent_session(session, payload.session_token)
    agent = agent_session.agent

    order = session.get(Order, payload.order_id)
    if not order or order.agent_id != agent.agent_id:
        raise HTTPException(status_code=404, detail="order not found")

    if order.status == "completed":
        return AuthoriseResponse(
            order_id=order.order_id, status="completed",
            settlement_tx=order.settlement_tx, card_id=order.card_id,
            receipt_url=f"/receipt/{order.order_id}",
        )

    if order.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f'order is "{order.status}" ({order.reason}); ask the merchant for a manual override first',
        )

    client = StraitsXCardClient()
    try:
        card = await client.issue_card(order.amount_sgd, cardholder_name=agent.name, order_id=order.order_id)
    except StraitsXError as e:
        payment_authority_score = score_payment_authority(succeeded=False)
        order.status = "failed"
        order.reason = str(e)
        session.add(order)
        session.commit()
        log_event(
            session, step="authorise", message=f"authorise failed: {e}",
            order_id=order.order_id, agent_id=agent.agent_id,
            detail={
                "denial_reason": "straitsx_error",
                "payment_authority_score": payment_authority_score,
                "identity_score": agent_session.identity_score,
                "mandate_scope_score": agent_session.mandate_scope_score,
                "behavior_score": agent.behavior_score,
                "commercial_validity_score": order.commercial_validity_score,
            },
        )
        raise HTTPException(status_code=402, detail=str(e))

    payment_authority_score = score_payment_authority(succeeded=True)
    live_trust_score = blend_authorise_score(
        identity_score=agent_session.identity_score,
        mandate_scope_score=agent_session.mandate_scope_score,
        behavior_score=agent.behavior_score,
        commercial_validity_score=order.commercial_validity_score,
    )
    score_breakdown = ScoreBreakdown(
        identity_score=agent_session.identity_score,
        mandate_scope_score=agent_session.mandate_scope_score,
        behavior_score=agent.behavior_score,
        commercial_validity_score=order.commercial_validity_score,
        payment_authority_score=payment_authority_score,
        live_trust_score=live_trust_score,
    )

    order.status = "completed"
    order.settlement_tx = card.settlement_tx
    order.card_id = card.card_id
    order.trust_score_at_checkout = live_trust_score
    order.receipt_token = sign_receipt({
        "order_id": order.order_id,
        "agent_id": agent.agent_id,
        "agent_name": agent.name,
        "sku": order.sku,
        "product_name": order.product_name,
        "amount_sgd": order.amount_sgd,
        "settlement_tx": card.settlement_tx,
        "card_id": card.card_id,
        "asset_address": card.asset_address,
        "mocked": card.mocked,
    })
    session.add(order)
    session.commit()
    session.refresh(order)

    log_event(
        session,
        step="authorise",
        message=f"Charged ${order.amount_sgd:.2f} via StraitsX{' (mock)' if card.mocked else ''} — settled {card.settlement_tx[:14]}…",
        order_id=order.order_id,
        agent_id=agent.agent_id,
        detail={
            "settlement_tx": card.settlement_tx, "card_id": card.card_id, "mocked": card.mocked,
            **score_breakdown.model_dump(),
        },
    )
    log_event(
        session,
        step="receipt",
        message=f"Signed receipt issued for order {order.order_id}",
        order_id=order.order_id,
        agent_id=agent.agent_id,
    )

    return AuthoriseResponse(
        order_id=order.order_id,
        status="completed",
        settlement_tx=card.settlement_tx,
        card_id=card.card_id,
        receipt_url=f"/receipt/{order.order_id}",
        score_breakdown=score_breakdown,
    )
