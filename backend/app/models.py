"""DB tables."""
import json
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.utcnow()


class Product(SQLModel, table=True):
    sku: str = Field(primary_key=True)
    name: str
    description: str
    category: str
    price_sgd: float


class Agent(SQLModel, table=True):
    agent_id: str = Field(primary_key=True)
    name: str
    session_token: str = Field(index=True)

    # Mandate (Section 5: "spend cap, merchant whitelist, expiry")
    spend_cap_sgd: float
    merchant_whitelist_json: str  # JSON list[str]
    expiry_hours: float

    # Identity signal (Section 7 trust score inputs)
    credential_issuer: Optional[str] = None
    credential_valid: bool = True

    # Revocation (security.py: checked live on every request, not just at issuance —
    # a still-unexpired token stops working the moment this flips false).
    key_active: bool = True
    key_revoked_at: Optional[datetime] = None

    # Trust score breakdown (Section 7 + 8.1 "not a black box")
    trust_score: float = 0
    mandate_scope_score: float = 0
    identity_score: float = 0
    behavior_score: float = 0

    identify_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    last_identify_at: datetime = Field(default_factory=utcnow)

    @property
    def merchant_whitelist(self) -> list[str]:
        return json.loads(self.merchant_whitelist_json)

    @property
    def expires_at(self) -> datetime:
        from datetime import timedelta
        return self.created_at + timedelta(hours=self.expiry_hours)


class Order(SQLModel, table=True):
    order_id: str = Field(primary_key=True)
    agent_id: str = Field(foreign_key="agent.agent_id", index=True)
    sku: str
    product_name: str
    category: str
    quantity: int
    amount_sgd: float

    # pending -> approved | blocked -> approved_override -> completed | failed
    status: str = "pending"
    reason: Optional[str] = None
    # "identity_verification_failure" | "commercial_validity_failure" | "insufficient_trust"
    # | "straitsx_error" | None — structured counterpart to `reason`'s free text, for
    # aggregate reporting (the merchant dashboard's blocked-reasons breakdown) without
    # parsing prose.
    denial_reason: Optional[str] = None

    trust_score_at_checkout: float = 0  # live_trust_score at whichever stage last computed it
    required_trust: float = 0
    commercial_validity_score: float = 100.0  # computed at /checkout, carried into /authorise's blend

    settlement_tx: Optional[str] = None
    card_id: Optional[str] = None
    receipt_token: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AuditEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: Optional[str] = Field(default=None, index=True)
    agent_id: Optional[str] = Field(default=None, index=True)
    step: str  # identify | checkout | authorise | receipt | override | blocked
    message: str
    detail_json: str = "{}"
    timestamp: datetime = Field(default_factory=utcnow, index=True)


class MerchantRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rule_type: str  # "category_cap" | "price_threshold" | "blocked_category"

    # category_cap: block purchases in `category` over `max_price_sgd` unless trust >= min_trust
    category: Optional[str] = None
    max_price_sgd: Optional[float] = None

    # price_threshold: purchases over `price_threshold_sgd` require trust >= min_trust
    price_threshold_sgd: Optional[float] = None

    min_trust: Optional[float] = None

    created_at: datetime = Field(default_factory=utcnow)
