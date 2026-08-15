"""StraitsX one-time card gateway client (PRD Section 9).

Mocked by default (MOCK_STRAITSX=true) so the rest of the platform never blocks on
sandbox access, per Section 9.6's build-order note. Set MOCK_STRAITSX=false once
`backend/scripts/discover_straitsx_mcp.py` has confirmed the real tool name/schema
and `_real_issue_card` below has been wired to it.
"""
import hashlib
import secrets
import time
from dataclasses import dataclass

from app.config import (
    MAX_CARD_AMOUNT_SGD,
    MIN_CARD_AMOUNT_SGD,
    MOCK_STRAITSX,
    STRAITSX_PRODUCTION_SSE,
    STRAITSX_PROFILE,
    STRAITSX_SANDBOX_SSE,
    XSGD_ADDRESS_PRODUCTION,
    XSGD_ADDRESS_SANDBOX,
)


class StraitsXError(Exception):
    pass


@dataclass
class CardResult:
    card_id: str
    settlement_tx: str
    asset_address: str
    amount_sgd: float
    mocked: bool


class StraitsXCardClient:
    def __init__(self, mock: bool = MOCK_STRAITSX, profile: str = STRAITSX_PROFILE):
        self.mock = mock
        self.profile = profile
        self.sse_url = STRAITSX_SANDBOX_SSE if profile == "sandbox" else STRAITSX_PRODUCTION_SSE
        self.asset_address = XSGD_ADDRESS_SANDBOX if profile == "sandbox" else XSGD_ADDRESS_PRODUCTION

    async def issue_card(self, amount_sgd: float, cardholder_name: str, order_id: str) -> CardResult:
        if amount_sgd < MIN_CARD_AMOUNT_SGD or amount_sgd > MAX_CARD_AMOUNT_SGD:
            raise StraitsXError(
                f"amount {amount_sgd:.2f} SGD outside card cap "
                f"{MIN_CARD_AMOUNT_SGD:.0f}-{MAX_CARD_AMOUNT_SGD:.0f} SGD"
            )
        if self.mock:
            return self._mock_issue_card(amount_sgd, cardholder_name, order_id)
        return await self._real_issue_card(amount_sgd, cardholder_name, order_id)

    def _mock_issue_card(self, amount_sgd: float, cardholder_name: str, order_id: str) -> CardResult:
        seed = f"{order_id}:{cardholder_name}:{amount_sgd}:{time.time()}"
        digest = hashlib.sha256(seed.encode()).hexdigest()
        return CardResult(
            card_id=f"card_mock_{digest[:16]}",
            settlement_tx=f"0x{digest[:64]}",
            asset_address=self.asset_address,
            amount_sgd=amount_sgd,
            mocked=True,
        )

    async def _real_issue_card(self, amount_sgd: float, cardholder_name: str, order_id: str) -> CardResult:
        """Not wired yet — see backend/scripts/discover_straitsx_mcp.py (PRD 9.2).

        Once the discovery script confirms the real tool name and input schema, this
        should open an `mcp.client.sse.sse_client(self.sse_url)` session, call
        `session.call_tool(<confirmed_tool_name>, {...confirmed params...})`, and map
        the result onto CardResult. Left raising NotImplementedError so a misconfigured
        MOCK_STRAITSX=false fails loudly instead of silently mocking a "real" charge.
        """
        raise NotImplementedError(
            "Real StraitsX MCP call not wired up yet. Run "
            "`python backend/scripts/discover_straitsx_mcp.py "
            f"{self.profile}` to get the tool name/schema, then implement this method. "
            "Set MOCK_STRAITSX=true to keep using the mock in the meantime."
        )


def new_order_id() -> str:
    return f"ord_{secrets.token_hex(8)}"


def new_agent_id() -> str:
    return f"agt_{secrets.token_hex(8)}"
