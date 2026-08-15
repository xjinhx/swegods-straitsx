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


class IdentifyResponse(BaseModel):
    agent_id: str
    session_token: str
    merchant: str
    trust: TrustBreakdown


class CheckoutRequest(BaseModel):
    session_token: str
    sku: str
    quantity: int = 1


class CheckoutResponse(BaseModel):
    order_id: str
    status: str
    reason: Optional[str] = None
    amount_sgd: float
    trust_score: float
    required_trust: float


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
    settlement_tx: Optional[str]
    created_at: str
