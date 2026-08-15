"""Trust scoring (PRD Section 7 "Trust score inputs", framed per arXiv 2604.03976 as a
continuous risk-adjustment score rather than a pass/fail gate).

PRD-trust-score-v2: the score is no longer one number frozen at /identify. Five
components, each 0-100 (or None where excluded):
  - mandate_scope_score:      narrower spend cap / whitelist / expiry = higher trust.
                               Frozen into the session token at /identify.
  - identity_score:           credential signature validity + issuer reputation.
                               Frozen into the session token at /identify.
  - behavior_score:           request velocity (repeat /identify attempts penalised).
                               Live — read fresh off the Agent row at every stage,
                               not frozen into the token.
  - commercial_validity_score: does the checkout content itself hold up (currently:
                               does the agent's believed price match the catalog)?
                               Computed live at /checkout, carried into /authorise.
  - payment_authority_score:  did StraitsX actually settle? Computed live at
                               /authorise; None on an infra-side failure (excluded
                               from the blend rather than penalising trust).

identity_score + mandate_scope_score answer "who is this agent" and are deliberately
frozen (security.py: a session token can't inherit a mandate change after issuance).
The other two answer "is *this* transaction valid" and are recomputed at each stage —
see blend_checkout_score / blend_authorise_score below.
"""
from datetime import datetime, timedelta

from app.schemas import Mandate

MANDATE_WEIGHT = 0.35
IDENTITY_WEIGHT = 0.40
BEHAVIOR_WEIGHT = 0.25

# /identify response blend: identity_score + mandate_scope_score renormalized without
# behavior (0.40/0.75, 0.35/0.75) — behavior no longer belongs in a *frozen* number,
# it's live from here on (see score_behavior's callers in checkout.py/authorise.py).
IDENTIFY_IDENTITY_WEIGHT = IDENTITY_WEIGHT / (IDENTITY_WEIGHT + MANDATE_WEIGHT)
IDENTIFY_MANDATE_WEIGHT = MANDATE_WEIGHT / (IDENTITY_WEIGHT + MANDATE_WEIGHT)

# /checkout live blend: frozen identity/mandate + live behavior + live commercial validity.
CHECKOUT_IDENTITY_WEIGHT = 0.30
CHECKOUT_MANDATE_WEIGHT = 0.25
CHECKOUT_BEHAVIOR_WEIGHT = 0.15
CHECKOUT_COMMERCIAL_WEIGHT = 0.30

# /authorise live blend: same four, weight redistributed to make room for payment authority.
AUTHORISE_IDENTITY_WEIGHT = 0.20
AUTHORISE_MANDATE_WEIGHT = 0.15
AUTHORISE_BEHAVIOR_WEIGHT = 0.10
AUTHORISE_COMMERCIAL_WEIGHT = 0.25
AUTHORISE_PAYMENT_WEIGHT = 0.30

# Below this, /checkout hard-denies regardless of the blended score (PRD Section 5.3) -
# a high identity/mandate score can't buy back a checkout whose contents don't check out.
COMMERCIAL_VALIDITY_GATE = 50.0

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


def score_commercial_validity(catalog_price_sgd: float, expected_price_sgd: float | None) -> tuple[float, str | None]:
    """Does the checkout content itself hold up against the catalog, not the agent's
    say-so? `expected_price_sgd` is what the agent believes it's paying (e.g. from a
    product page it read earlier, or a prompt-injected instruction) — if it disagrees
    with the live catalog price by more than 5%, that's a tampered/stale checkout, not
    a trust-of-the-agent question. Omitted entirely (no assertion made) scores 100:
    nothing to check.

    Note: SKU-not-found and merchant-mismatch checks from the original design aren't
    reachable here — /checkout 404s on an unknown SKU before this runs, and this is a
    single-merchant deployment with no per-product merchant field to mismatch.
    """
    if expected_price_sgd is None:
        return 100.0, None
    diff_pct = abs(expected_price_sgd - catalog_price_sgd) / catalog_price_sgd
    if diff_pct > 0.05:
        return 20.0, (
            f"checkout asserted {expected_price_sgd:.2f} SGD but catalog price is "
            f"{catalog_price_sgd:.2f} SGD ({diff_pct:.0%} mismatch)"
        )
    return 100.0, None


def score_payment_authority(succeeded: bool) -> float | None:
    """Grades StraitsX's settlement outcome instead of treating it as a bare boolean.

    Collapsed to 2 outcomes, not the original 4-tier design: StraitsX's card issuance
    is binary in practice (a single-use card issues at the exact requested amount, or
    raises StraitsXError) — there's no "authorized at a reduced amount" response to
    grade. And because mandate.spend_cap_sgd is already hard-checked at /checkout
    (before /authorise ever calls StraitsX), a StraitsXError here is always an
    infra/protocol failure, never "declined - insufficient mandate scope" - so `None`
    (excluded from the blend, logged separately) covers every failure case honestly.
    """
    return 100.0 if succeeded else None


def compute_trust_score(
    mandate: Mandate, credential: str, issuer: str | None, identify_count_in_window: int
) -> dict:
    """Computed once at /identify. `trust_score` here is the *identify-stage* blend —
    identity_score + mandate_scope_score only (IDENTIFY_IDENTITY_WEIGHT/IDENTIFY_MANDATE_WEIGHT).
    behavior_score is still returned for display and stored live on the Agent row, but
    is deliberately excluded from this number: it's no longer frozen into anything —
    see blend_checkout_score / blend_authorise_score, which read it fresh at each stage.
    """
    mandate_scope_score = score_mandate_scope(mandate)
    identity_score = score_identity(credential, issuer)
    behavior_score = score_behavior(identify_count_in_window)

    identify_trust_score = (
        identity_score * IDENTIFY_IDENTITY_WEIGHT
        + mandate_scope_score * IDENTIFY_MANDATE_WEIGHT
    )

    return {
        "mandate_scope_score": mandate_scope_score,
        "identity_score": identity_score,
        "behavior_score": behavior_score,
        "trust_score": round(clamp(identify_trust_score), 1),
    }


def blend_checkout_score(
    identity_score: float, mandate_scope_score: float, behavior_score: float, commercial_validity_score: float
) -> float:
    return round(clamp(
        identity_score * CHECKOUT_IDENTITY_WEIGHT
        + mandate_scope_score * CHECKOUT_MANDATE_WEIGHT
        + behavior_score * CHECKOUT_BEHAVIOR_WEIGHT
        + commercial_validity_score * CHECKOUT_COMMERCIAL_WEIGHT
    ), 1)


def blend_authorise_score(
    identity_score: float, mandate_scope_score: float, behavior_score: float, commercial_validity_score: float
) -> float:
    """Only called when payment_authority_score is 100 (StraitsX succeeded) — an infra
    failure has nothing meaningful to blend into a "trust" number (score_payment_authority's
    docstring), so authorise.py logs those with the component scores as context and no
    forced composite, instead of calling this."""
    return round(clamp(
        identity_score * AUTHORISE_IDENTITY_WEIGHT
        + mandate_scope_score * AUTHORISE_MANDATE_WEIGHT
        + behavior_score * AUTHORISE_BEHAVIOR_WEIGHT
        + commercial_validity_score * AUTHORISE_COMMERCIAL_WEIGHT
        + 100.0 * AUTHORISE_PAYMENT_WEIGHT
    ), 1)


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
