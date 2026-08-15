"""StraitsX one-time card gateway client.

Mocked by default (MOCK_STRAITSX=true) so the rest of the platform never blocks on
sandbox access.

The real flow (confirmed live against the sandbox server) starts with
an actual MCP tool call, then drops into an x402 payment challenge on top of a REST
endpoint the tool call points us at:
  1. Over the card gateway's MCP session (SSE transport), call `get_card_sandbox` /
     `get_card_prod` with {wallet_address, cardholder_name, amount_sgd}. The tool
     returns the cardapi URL and body to use — not the card itself.
  2. POST that body to that URL. Server replies 402 with a JSON body describing the
     required payment (asset, amount, payTo, chainId, EIP-3009 domain name/version).
  3. Sign an EIP-3009 TransferWithAuthorization for that amount with our wallet key.
  4. Retry the same POST with a base64-encoded PAYMENT-SIGNATURE header — the encoded
     payload must echo back the accepted requirement (`"accepted": requirement`), not
     just the signature, or the server can't resolve the atomic amount it's verifying.
  5. Server returns card_opaque_id / card_html / settlement_tx.
"""
import base64
import hashlib
import json
import logging
import re
import secrets
import time
from dataclasses import dataclass

import httpx
from eth_account import Account
from eth_utils import to_checksum_address
from mcp import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)

from app.config import (
    MAX_CARD_AMOUNT_SGD,
    MIN_CARD_AMOUNT_SGD,
    MOCK_STRAITSX,
    STRAITSX_PROFILE,
    STRAITSX_PRODUCTION_SSE,
    STRAITSX_SANDBOX_SSE,
    STRAITSX_WALLET_ADDRESS,
    STRAITSX_WALLET_PRIVATE_KEY,
    XSGD_ADDRESS_PRODUCTION,
    XSGD_ADDRESS_SANDBOX,
    XSGD_CHAIN_ID_PRODUCTION,
    XSGD_CHAIN_ID_SANDBOX,
)


class StraitsXError(Exception):
    pass


def _sanitize_cardholder_name(name: str) -> str:
    """StraitsX's card issuer requires 2-26 chars, letters and spaces only.

    Agent names (e.g. "test-script-agent") come from `/identify` with no such
    constraint — a hyphenated or otherwise non-conforming name breaks the issuer's
    surname/first-name split downstream (confirmed via a direct MCP call: an
    unsanitized name produced "'{surname}/{first_name}' length (35) must be ... no
    greater than 26"), so normalize before it ever reaches StraitsX.
    """
    cleaned = re.sub(r"[^A-Za-z ]+", " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 2:
        cleaned = "Agent Customer"
    return cleaned[:26].strip()


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
        self.mcp_tool_name = "get_card_sandbox" if profile == "sandbox" else "get_card_prod"
        self.asset_address = XSGD_ADDRESS_SANDBOX if profile == "sandbox" else XSGD_ADDRESS_PRODUCTION
        self.chain_id = XSGD_CHAIN_ID_SANDBOX if profile == "sandbox" else XSGD_CHAIN_ID_PRODUCTION
        self.wallet_address = STRAITSX_WALLET_ADDRESS
        self.wallet_private_key = STRAITSX_WALLET_PRIVATE_KEY

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
        """Call the card gateway's MCP tool, then pay the x402 challenge it points at.

        See module docstring for the flow. Field names on the success response
        (card_opaque_id / card_html / settlement_tx) come from StraitsX's own tool
        description, not an executed live call — if the server's shape differs,
        this raises StraitsXError with the raw body rather than guessing.
        """
        if not self.wallet_address or not self.wallet_private_key:
            raise StraitsXError(
                "STRAITSX_WALLET_ADDRESS / STRAITSX_WALLET_PRIVATE_KEY not set in "
                "backend/.env — required to sign the EIP-3009 payment authorization."
            )

        cardholder_name = _sanitize_cardholder_name(cardholder_name)
        cardapi_url, body = await self._mcp_get_card_instructions(amount_sgd, cardholder_name)

        async with httpx.AsyncClient(timeout=30) as client:
            challenge_resp = await client.post(cardapi_url, json=body)
            if challenge_resp.status_code != 402:
                raise StraitsXError(
                    f"expected HTTP 402 payment challenge, got {challenge_resp.status_code}: "
                    f"{challenge_resp.text}"
                )

            challenge = challenge_resp.json()
            try:
                requirement = challenge["accepts"][0]
            except (KeyError, IndexError) as exc:
                raise StraitsXError(f"malformed x402 challenge: {challenge}") from exc

            logger.warning(
                "StraitsX %s charge about to be signed: order=%s amount_sgd=%.2f "
                "from=%s payTo=%s asset=%s chainId=%s atomic_amount=%s network=%s",
                self.profile, order_id, amount_sgd, self.wallet_address,
                requirement.get("payTo"), requirement.get("asset"), requirement.get("chainId"),
                requirement.get("amount"), requirement.get("network"),
            )

            payment_header = self._sign_payment(requirement)

            paid_resp = await client.post(
                cardapi_url,
                json=body,
                headers={"PAYMENT-SIGNATURE": payment_header},
            )
            if paid_resp.status_code != 200:
                raise StraitsXError(
                    f"card issuance failed after payment, HTTP {paid_resp.status_code}: "
                    f"{paid_resp.text}"
                )

            result = paid_resp.json()
            try:
                return CardResult(
                    card_id=result["card_opaque_id"],
                    settlement_tx=result["settlement_tx"],
                    asset_address=self.asset_address,
                    amount_sgd=amount_sgd,
                    mocked=False,
                )
            except KeyError as exc:
                raise StraitsXError(
                    f"card issued but response shape unexpected, missing {exc}: {result}"
                ) from exc

    async def _mcp_get_card_instructions(self, amount_sgd: float, cardholder_name: str) -> tuple[str, dict]:
        """Ask the card gateway's MCP server (SSE transport) where and what to POST.

        `get_card_sandbox` / `get_card_prod` don't issue the card themselves — they
        return the cardapi URL and the exact body to send it, which we then drive
        through the x402 challenge/pay/retry dance in `_real_issue_card`.
        """
        async with sse_client(self.sse_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_result = await session.call_tool(self.mcp_tool_name, {
                    "wallet_address": self.wallet_address,
                    "cardholder_name": cardholder_name,
                    "amount_sgd": amount_sgd,
                })
                if tool_result.is_error:
                    raise StraitsXError(f"MCP {self.mcp_tool_name} call failed: {tool_result.content}")
                instructions = json.loads(tool_result.content[0].text)

        try:
            return instructions["url"], instructions["body"]
        except KeyError as exc:
            raise StraitsXError(
                f"MCP {self.mcp_tool_name} response missing {exc}: {instructions}"
            ) from exc

    def _sign_payment(self, requirement: dict) -> str:
        """Build and sign the EIP-3009 TransferWithAuthorization for one x402 `accepts` entry.

        Reconciles the challenge's asset/chainId against the active profile's expected
        XSGD config before signing anything — otherwise we'd blindly sign whatever the
        server claims, with no client-side guarantee it's actually paying on the network
        (sandbox vs. production) we think we're on. This matters most for production:
        a mismatch there would mean signing a real-value transfer on the wrong say-so.
        """
        extra = requirement.get("extra", {})
        pay_to = to_checksum_address(requirement["payTo"])
        asset = to_checksum_address(requirement["asset"])
        payer = to_checksum_address(self.wallet_address)
        value = int(requirement["amount"])
        chain_id = int(requirement["chainId"])

        expected_asset = to_checksum_address(self.asset_address)
        if asset != expected_asset:
            raise StraitsXError(
                f"x402 challenge asset {asset} does not match {self.profile} XSGD "
                f"{expected_asset} — refusing to sign"
            )
        if chain_id != self.chain_id:
            raise StraitsXError(
                f"x402 challenge chainId {chain_id} does not match {self.profile} chain "
                f"{self.chain_id} — refusing to sign"
            )

        valid_before = int(time.time()) + int(requirement.get("maxTimeoutSeconds", 300))
        nonce = secrets.token_bytes(32)

        typed_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                ],
            },
            "primaryType": "TransferWithAuthorization",
            "domain": {
                "name": extra.get("name", "XSGD"),
                "version": extra.get("version", "2"),
                "chainId": chain_id,
                "verifyingContract": asset,
            },
            "message": {
                "from": payer,
                "to": pay_to,
                "value": value,
                "validAfter": 0,
                "validBefore": valid_before,
                "nonce": nonce,
            },
        }
        signed = Account.sign_typed_data(self.wallet_private_key, full_message=typed_data)
        signature_hex = signed.signature.hex()
        if not signature_hex.startswith("0x"):
            signature_hex = "0x" + signature_hex

        logger.info(
            "sign_payment: requirement[amount]=%r (%s) -> parsed atomic value=%s -> authorization.value=%r",
            requirement.get("amount"), type(requirement.get("amount")).__name__,
            value, str(value),
        )

        payload = {
            "x402Version": 1,
            "scheme": requirement["scheme"],
            "network": requirement["network"],
            "accepted": requirement,
            "payload": {
                "signature": signature_hex,
                "authorization": {
                    "from": payer,
                    "to": pay_to,
                    "value": str(value),
                    "validAfter": "0",
                    "validBefore": str(valid_before),
                    "nonce": "0x" + nonce.hex(),
                },
            },
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()


def new_order_id() -> str:
    return f"ord_{secrets.token_hex(8)}"


def new_agent_id() -> str:
    return f"agt_{secrets.token_hex(8)}"
