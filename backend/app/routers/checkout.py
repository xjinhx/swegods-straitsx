"""POST /checkout — PRD Section 6 step 5. PRD-trust-score-v2: the authorization decision
now runs against a live_trust_score (frozen identity/mandate + live behavior + live
commercial_validity), not the score frozen at /identify, and commercial_validity_score
is a hard gate independent of the blend — a tampered checkout can't be bought back by a
high identity score (Section 5.3)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.audit import log_event
from app.config import MAX_CARD_AMOUNT_SGD, MERCHANT_NAME, MIN_CARD_AMOUNT_SGD
from app.database import get_session
from app.deps import get_agent_session
from app.models import Order, Product
from app.rules import evaluate
from app.schemas import CheckoutRequest, CheckoutResponse, ScoreBreakdown
from app.straitsx_client import new_order_id
from app.trust import COMMERCIAL_VALIDITY_GATE, blend_checkout_score, score_commercial_validity

router = APIRouter(tags=["checkout"])


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest, session: Session = Depends(get_session)):
    agent_session = get_agent_session(session, payload.session_token)
    agent = agent_session.agent
    mandate = agent_session.mandate

    whitelist = mandate.merchant_whitelist
    if whitelist and MERCHANT_NAME not in whitelist and "*" not in whitelist:
        raise HTTPException(
            status_code=403,
            detail=f'mandate does not authorise purchases at "{MERCHANT_NAME}" (whitelist: {whitelist})',
        )

    product = session.get(Product, payload.sku)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be at least 1")

    amount_sgd = round(product.price_sgd * payload.quantity, 2)

    commercial_validity_score, commercial_reason = score_commercial_validity(
        product.price_sgd, payload.expected_price_sgd
    )
    live_trust_score = blend_checkout_score(
        identity_score=agent_session.identity_score,
        mandate_scope_score=agent_session.mandate_scope_score,
        behavior_score=agent.behavior_score,
        commercial_validity_score=commercial_validity_score,
    )

    denial_reason = None
    if commercial_validity_score < COMMERCIAL_VALIDITY_GATE:
        decision_allowed, required_trust, reason = False, 101, commercial_reason
        denial_reason = "commercial_validity_failure"
    elif amount_sgd > mandate.spend_cap_sgd:
        decision_allowed, required_trust, reason = False, 101, (
            f"amount {amount_sgd:.2f} SGD exceeds mandate spend cap {mandate.spend_cap_sgd:.2f} SGD"
        )
        denial_reason = "insufficient_trust"
    elif amount_sgd < MIN_CARD_AMOUNT_SGD or amount_sgd > MAX_CARD_AMOUNT_SGD:
        decision_allowed, required_trust, reason = False, 101, (
            f"amount {amount_sgd:.2f} SGD is outside the card issuance range "
            f"{MIN_CARD_AMOUNT_SGD:.0f}-{MAX_CARD_AMOUNT_SGD:.0f} SGD — reduce quantity and try again"
        )
        denial_reason = "insufficient_trust"
    else:
        decision = evaluate(session, product.category, amount_sgd, live_trust_score)
        decision_allowed, required_trust, reason = decision.allowed, decision.required_trust, decision.reason
        if not decision_allowed:
            denial_reason = "insufficient_trust"

    order = Order(
        order_id=new_order_id(),
        agent_id=agent.agent_id,
        sku=product.sku,
        product_name=product.name,
        category=product.category,
        quantity=payload.quantity,
        amount_sgd=amount_sgd,
        status="approved" if decision_allowed else "blocked",
        reason=reason,
        trust_score_at_checkout=live_trust_score,
        required_trust=required_trust,
        commercial_validity_score=commercial_validity_score,
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    score_breakdown = ScoreBreakdown(
        identity_score=agent_session.identity_score,
        mandate_scope_score=agent_session.mandate_scope_score,
        behavior_score=agent.behavior_score,
        commercial_validity_score=commercial_validity_score,
        live_trust_score=live_trust_score,
    )

    log_event(
        session,
        step="checkout" if decision_allowed else "blocked",
        message=(
            f'Agent "{agent.name}" requested {product.name} (${amount_sgd:.2f}) — '
            f"trust {live_trust_score:.0f} — "
            + (f"approved (required {required_trust:.0f})" if decision_allowed else f"blocked: {reason}")
        ),
        order_id=order.order_id,
        agent_id=agent.agent_id,
        detail={
            **score_breakdown.model_dump(),
            "sku": product.sku,
            "amount_sgd": amount_sgd,
            "required_trust": required_trust,
            "reason": reason,
            "denial_reason": denial_reason,
        },
    )

    return CheckoutResponse(
        order_id=order.order_id,
        status=order.status,
        reason=reason,
        denial_reason=denial_reason,
        amount_sgd=amount_sgd,
        trust_score=live_trust_score,
        required_trust=required_trust,
        score_breakdown=score_breakdown,
    )
