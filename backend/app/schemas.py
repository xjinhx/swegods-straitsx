from typing import Optional

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    sku: str
    name: str
    description: str
    category: str
    price_sgd: float


class Mandate(BaseModel):
    spend_cap_sgd: float = Field(gt=0)
    merchant_whitelist: list[str] = Field(default_factory=list)
    expiry_hours: float = Field(gt=0, default=24)


class IdentifyRequest(BaseModel):
    agent_name: str
    credential: str  # mocked signed credential blob (JWT-shaped or opaque)
    issuer: Optional[str] = None
    mandate: Mandate


class TrustBreakdown(BaseModel):
    mandate_scope_score: float
    identity_score: float
    behavior_score: float
    trust_score: float
    # behavior_score's inputs at the agent-summary level (merchant.py) — same fields as
    # ScoreBreakdown, kept optional since a brand-new agent has no order history yet.
    reputation_score: Optional[float] = None
    reputation_orders: Optional[str] = None


class IdentifyResponse(BaseModel):
    agent_id: str
    session_token: str
    merchant: str
    trust: TrustBreakdown


class CheckoutRequest(BaseModel):
    session_token: str
    sku: str
    quantity: int = 1
    # What the agent believes the price is (e.g. from a product page read earlier, or a
    # prompt-injected instruction) — optional; omitted means no assertion to check.
    # Compared against the live catalog price by commercial_validity_score.
    expected_price_sgd: Optional[float] = None


class ScoreBreakdown(BaseModel):
    identity_score: float
    mandate_scope_score: float
    behavior_score: float
    commercial_validity_score: Optional[float] = None
    payment_authority_score: Optional[float] = None
    # behavior_score's inputs, surfaced so the dashboard can show *why*: a Wilson-score
    # reputation over the agent's own resolved order history (None = no track record yet).
    reputation_score: Optional[float] = None
    reputation_orders: Optional[str] = None  # e.g. "3/4 past orders succeeded"
    live_trust_score: Optional[float] = None


class CheckoutResponse(BaseModel):
    order_id: str
    status: str
    reason: Optional[str] = None
    denial_reason: Optional[str] = None  # "commercial_validity_failure" | "insufficient_trust"
    amount_sgd: float
    trust_score: float
    required_trust: float
    score_breakdown: Optional[ScoreBreakdown] = None


class AuthoriseRequest(BaseModel):
    session_token: str
    order_id: str


class AuthoriseResponse(BaseModel):
    order_id: str
    status: str
    settlement_tx: Optional[str] = None
    card_id: Optional[str] = None
    receipt_url: Optional[str] = None
    reason: Optional[str] = None
    denial_reason: Optional[str] = None  # "straitsx_error" when payment_authority_score is None
    score_breakdown: Optional[ScoreBreakdown] = None


class ReceiptOut(BaseModel):
    order_id: str
    signed_receipt: str
    agent_id: str
    sku: str
    amount_sgd: float
    settlement_tx: Optional[str]
    issued_at: str


class AuditEventOut(BaseModel):
    id: int
    order_id: Optional[str]
    agent_id: Optional[str]
    step: str
    message: str
    detail: dict
    timestamp: str


class OverrideRequest(BaseModel):
    note: Optional[str] = None


class RuleIn(BaseModel):
    rule_type: str
    category: Optional[str] = None
    max_price_sgd: Optional[float] = None
    price_threshold_sgd: Optional[float] = None
    min_trust: Optional[float] = None


class RuleOut(RuleIn):
    id: int
    created_at: str


class OrderOut(BaseModel):
    order_id: str
    agent_id: str
    agent_name: str
    sku: str
    product_name: str
    category: str
    amount_sgd: float
    status: str
    reason: Optional[str]
    trust_score_at_checkout: float
    required_trust: float
    commercial_validity_score: float
    settlement_tx: Optional[str]
    created_at: str
