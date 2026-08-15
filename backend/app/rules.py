"""Merchant decision layer (PRD Section 8.2 rule builder + Section 13's framing of this
as the "missing internal decision model", arXiv 2607.18347).

`/checkout` reads live from MerchantRule rows instead of hardcoded thresholds, so the
merchant dashboard's rule builder has real effect (Section 8.2) without any extra
backend logic beyond this evaluation.
"""
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import MerchantRule
from app.trust import default_required_trust


@dataclass
class Decision:
    allowed: bool
    required_trust: float
    reason: str | None


def evaluate(session: Session, category: str, amount_sgd: float, trust_score: float) -> Decision:
    rules = session.exec(select(MerchantRule)).all()

    for rule in rules:
        if rule.rule_type == "blocked_category" and rule.category == category:
            return Decision(allowed=False, required_trust=101, reason=f'category "{category}" is blocked by merchant rule')

    required_trust = default_required_trust(amount_sgd)
    price_threshold_rules = [r for r in rules if r.rule_type == "price_threshold" and r.price_threshold_sgd is not None]
    for rule in sorted(price_threshold_rules, key=lambda r: r.price_threshold_sgd, reverse=True):
        if amount_sgd >= rule.price_threshold_sgd:
            required_trust = rule.min_trust or 0
            break

    for rule in rules:
        if rule.rule_type == "category_cap" and rule.category == category and rule.max_price_sgd is not None:
            if amount_sgd > rule.max_price_sgd:
                cap_required_trust = rule.min_trust if rule.min_trust is not None else 100
                required_trust = max(required_trust, cap_required_trust)

    if trust_score < required_trust:
        return Decision(
            allowed=False,
            required_trust=required_trust,
            reason=f"trust score {trust_score:.0f} below required {required_trust:.0f} for this purchase",
        )
    return Decision(allowed=True, required_trust=required_trust, reason=None)
