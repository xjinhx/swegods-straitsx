"""Merchant-facing endpoints — PRD Section 8 (the human merchant's side, not the
agent's). Reuses data the core flow already generates; the rule builder is the only
place with new state (MerchantRule rows that /checkout reads from, see app/rules.py)."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.audit import log_event
from app.database import get_session
from app.models import Agent, MerchantRule, Order
from app.schemas import OrderOut, OverrideRequest, RuleIn, RuleOut, TrustBreakdown

router = APIRouter(prefix="/merchant", tags=["merchant"])


@router.get("/agents/{agent_id}/trust", response_model=TrustBreakdown)
def agent_trust(agent_id: str, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
    return TrustBreakdown(
        mandate_scope_score=agent.mandate_scope_score,
        identity_score=agent.identity_score,
        behavior_score=agent.behavior_score,
        trust_score=agent.trust_score,
    )


@router.get("/agents")
def list_agents(session: Session = Depends(get_session)):
    agents = session.exec(select(Agent).order_by(Agent.last_identify_at.desc())).all()
    return [
        {
            "agent_id": a.agent_id,
            "name": a.name,
            "trust_score": a.trust_score,
            "mandate_scope_score": a.mandate_scope_score,
            "identity_score": a.identity_score,
            "behavior_score": a.behavior_score,
            "spend_cap_sgd": a.spend_cap_sgd,
            "merchant_whitelist": a.merchant_whitelist,
            "identify_count": a.identify_count,
            "last_identify_at": a.last_identify_at.isoformat() + "Z",
        }
        for a in agents
    ]


@router.get("/orders", response_model=list[OrderOut])
def list_orders(session: Session = Depends(get_session)):
    orders = session.exec(select(Order).order_by(Order.created_at.desc())).all()
    out = []
    for o in orders:
        agent = session.get(Agent, o.agent_id)
        out.append(OrderOut(
            order_id=o.order_id, agent_id=o.agent_id, agent_name=agent.name if agent else "unknown",
            sku=o.sku, product_name=o.product_name, category=o.category, amount_sgd=o.amount_sgd,
            status=o.status, reason=o.reason, trust_score_at_checkout=o.trust_score_at_checkout,
            required_trust=o.required_trust, commercial_validity_score=o.commercial_validity_score,
            settlement_tx=o.settlement_tx, created_at=o.created_at.isoformat() + "Z",
        ))
    return out


@router.post("/orders/{order_id}/override")
def override_order(order_id: str, payload: OverrideRequest, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    if order.status != "blocked":
        raise HTTPException(status_code=409, detail=f'order is "{order.status}", not blocked — nothing to override')

    order.status = "approved_override"
    order.reason = (order.reason or "") + " — manually overridden by merchant"
    session.add(order)
    session.commit()

    log_event(
        session, step="override",
        message=f"Merchant manually approved blocked order {order_id}" + (f" ({payload.note})" if payload.note else ""),
        order_id=order_id, agent_id=order.agent_id,
        detail={"note": payload.note},
    )
    return {"order_id": order_id, "status": order.status}


@router.get("/rules", response_model=list[RuleOut])
def list_rules(session: Session = Depends(get_session)):
    rules = session.exec(select(MerchantRule).order_by(MerchantRule.created_at)).all()
    return [RuleOut(
        id=r.id, rule_type=r.rule_type, category=r.category, max_price_sgd=r.max_price_sgd,
        price_threshold_sgd=r.price_threshold_sgd, min_trust=r.min_trust,
        created_at=r.created_at.isoformat() + "Z",
    ) for r in rules]


VALID_RULE_TYPES = {"category_cap", "price_threshold", "blocked_category"}


@router.post("/rules", response_model=RuleOut)
def create_rule(payload: RuleIn, session: Session = Depends(get_session)):
    if payload.rule_type not in VALID_RULE_TYPES:
        raise HTTPException(status_code=400, detail=f"rule_type must be one of {sorted(VALID_RULE_TYPES)}")
    if payload.rule_type in {"category_cap", "blocked_category"} and not payload.category:
        raise HTTPException(status_code=400, detail=f'"{payload.rule_type}" requires a category')
    if payload.rule_type == "price_threshold" and payload.price_threshold_sgd is None:
        raise HTTPException(status_code=400, detail='"price_threshold" requires price_threshold_sgd')
    if payload.rule_type in {"category_cap", "price_threshold"} and payload.min_trust is None:
        raise HTTPException(status_code=400, detail=f'"{payload.rule_type}" requires min_trust')

    rule = MerchantRule(**payload.model_dump())
    session.add(rule)
    session.commit()
    session.refresh(rule)

    log_event(session, step="rule_created", message=f"Merchant added rule: {_describe_rule(rule)}", detail=json.loads(rule.model_dump_json()))
    return RuleOut(
        id=rule.id, rule_type=rule.rule_type, category=rule.category, max_price_sgd=rule.max_price_sgd,
        price_threshold_sgd=rule.price_threshold_sgd, min_trust=rule.min_trust,
        created_at=rule.created_at.isoformat() + "Z",
    )


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    rule = session.get(MerchantRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    session.delete(rule)
    session.commit()
    log_event(session, step="rule_deleted", message=f"Merchant removed rule #{rule_id}: {_describe_rule(rule)}")
    return {"deleted": rule_id}


def _describe_rule(rule: MerchantRule) -> str:
    if rule.rule_type == "blocked_category":
        return f'block category "{rule.category}"'
    min_trust = f"{rule.min_trust:.0f}" if rule.min_trust is not None else "n/a"
    if rule.rule_type == "category_cap":
        max_price = f"{rule.max_price_sgd:.2f}" if rule.max_price_sgd is not None else "n/a"
        return f'"{rule.category}" capped at ${max_price} for trust < {min_trust}'
    price_threshold = f"{rule.price_threshold_sgd:.2f}" if rule.price_threshold_sgd is not None else "n/a"
    return f"purchases ≥ ${price_threshold} require trust ≥ {min_trust}"
