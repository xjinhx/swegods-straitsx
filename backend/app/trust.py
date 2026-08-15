"""Trust scoring (PRD Section 7 "Trust score inputs", framed per arXiv 2604.03976 as a
continuous risk-adjustment score rather than a pass/fail gate).

Three weighted components, each 0-100:
  - mandate_scope_score: narrower spend cap / whitelist / expiry = higher trust
  - identity_score:      credential signature validity + issuer reputation
  - behavior_score:      request velocity (repeat /identify attempts penalised)
"""
from datetime import datetime, timedelta

from app.schemas import Mandate

MANDATE_WEIGHT = 0.35
IDENTITY_WEIGHT = 0.40
BEHAVIOR_WEIGHT = 0.25

# Issuers we recognise as reputable for demo purposes (Section 7: "issuer reputation
# if available"). Anything else still passes signature-shape validation but scores lower.
TRUSTED_ISSUERS = {"demo-agent-v1", "claude-agent-sdk", "agentmart-reference-agent"}

IDENTIFY_VELOCITY_WINDOW = timedelta(minutes=5)
IDENTIFY_VELOCITY_PENALTY = 15
IDENTIFY_VELOCITY_FLOOR = 10


def clamp(value: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def score_mandate_scope(mandate: Mandate) -> float:
    # Tighter spend cap -> higher trust. 30 SGD (our card ceiling) or below scores ~94+.
    spend_cap_score = clamp(100 - (mandate.spend_cap_sgd / 5))

    n = len(mandate.merchant_whitelist)
    if n == 0:
        whitelist_score = 20  # unrestricted mandate = least trustworthy
    elif n <= 3:
        whitelist_score = 100
    elif n <= 10:
        whitelist_score = 60
    else:
        whitelist_score = 30

    if mandate.expiry_hours <= 24:
        expiry_score = 100
    elif mandate.expiry_hours <= 24 * 7:
        expiry_score = 75
    elif mandate.expiry_hours <= 24 * 30:
        expiry_score = 50
    else:
        expiry_score = 25

    return round((spend_cap_score + whitelist_score + expiry_score) / 3, 1)


def score_identity(credential: str, issuer: str | None) -> float:
    # Mocked signature check: non-goal 4 rules out full PKI, so we validate *shape*
    # (long enough, three dot-separated segments like a JWT) rather than a real signature.
    looks_signed = bool(credential) and len(credential) >= 20 and credential.count(".") >= 2
    if not looks_signed:
        return 20
    if issuer in TRUSTED_ISSUERS:
        return 100
    return 70


def score_behavior(identify_count_in_window: int) -> float:
    penalty = max(0, identify_count_in_window - 1) * IDENTIFY_VELOCITY_PENALTY
    return clamp(100 - penalty, IDENTIFY_VELOCITY_FLOOR, 100)


def compute_trust_score(
    mandate: Mandate, credential: str, issuer: str | None, identify_count_in_window: int
) -> dict:
    mandate_scope_score = score_mandate_scope(mandate)
    identity_score = score_identity(credential, issuer)
    behavior_score = score_behavior(identify_count_in_window)

    overall = (
        mandate_scope_score * MANDATE_WEIGHT
        + identity_score * IDENTITY_WEIGHT
        + behavior_score * BEHAVIOR_WEIGHT
    )

    return {
        "mandate_scope_score": mandate_scope_score,
        "identity_score": identity_score,
        "behavior_score": behavior_score,
        "trust_score": round(clamp(overall), 1),
    }


# ---- Default required-trust tiers, used when no merchant price_threshold rule exists
# (PRD Section 8.2: merchant can override these via the rule builder). ----
DEFAULT_PRICE_TIERS = [
    (30.0, 80),
    (20.0, 65),
    (10.0, 40),
    (0.0, 0),
]


def default_required_trust(amount_sgd: float) -> float:
    for floor, required in DEFAULT_PRICE_TIERS:
        if amount_sgd >= floor:
            return required
    return 0
