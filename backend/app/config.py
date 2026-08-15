"""Central config, read from environment variables (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

MERCHANT_NAME = os.getenv("MERCHANT_NAME", "AgentMart")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentmart.db")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"

# StraitsX card-issuing MCP (PRD Section 9). Cards are single-use, 5-30 SGD.
MOCK_STRAITSX = os.getenv("MOCK_STRAITSX", "true").lower() == "true"
STRAITSX_PROFILE = os.getenv("STRAITSX_PROFILE", "sandbox")  # "sandbox" | "production"
STRAITSX_SANDBOX_SSE = "https://card.straitsx.ai/sandbox/sse"
STRAITSX_PRODUCTION_SSE = "https://card.straitsx.ai/production/sse"

# REST endpoint behind an x402 payment challenge (PRD Section 9.2 discovery finding:
# the MCP tool itself only returns payment requirements, the actual card issuance is
# this HTTP call, paid via a signed EIP-3009 TransferWithAuthorization).
STRAITSX_SANDBOX_CARDAPI = "https://card.straitsx.ai/sandbox/cardapi/issue_card"
STRAITSX_PRODUCTION_CARDAPI = "https://card.straitsx.ai/production/cardapi/issue_card"

# Wallet that signs the EIP-3009 TransferWithAuthorization paying the x402
# challenge returned by StraitsX's cardapi.
STRAITSX_WALLET_ADDRESS = os.getenv("STRAITSX_WALLET_ADDRESS", "")
STRAITSX_WALLET_PRIVATE_KEY = os.getenv("STRAITSX_WALLET_PRIVATE_KEY", "")

MIN_CARD_AMOUNT_SGD = 5.0
MAX_CARD_AMOUNT_SGD = 30.0

# Sandbox XSGD, Fuji (eip155:43113) / production XSGD, Avalanche C-Chain (eip155:43114)
# confirmed via live StraitsX responses, PRD Section 9.4.
XSGD_ADDRESS_SANDBOX = "0xd769410dc8772695a7f55a304d2125320a65c2a5"
XSGD_ADDRESS_PRODUCTION = "0xb2f85b7ab3c2b6f62df06de6ae7d09c010a5096e"

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
