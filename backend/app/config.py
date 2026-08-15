"""Central config, read from environment variables (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

MERCHANT_NAME = os.getenv("MERCHANT_NAME", "AgentMart")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentmart.db")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"

# StraitsX card-issuing MCP (PRD Section 9). Cards are single-use, 5-30 SGD.
# Hackathon requirement (docs_folder/developer.md): the final solution must settle in
# real $XSGD on Avalanche C-Chain Mainnet (43114) — Fuji/sandbox (43113) is for local
# testing only. Defaults to production; set STRAITSX_PROFILE=sandbox to test locally.
MOCK_STRAITSX = os.getenv("MOCK_STRAITSX", "true").lower() == "true"
STRAITSX_PROFILE = os.getenv("STRAITSX_PROFILE", "production")  # "sandbox" | "production"
STRAITSX_SANDBOX_SSE = "https://card.straitsx.ai/sandbox/sse"
STRAITSX_PRODUCTION_SSE = "https://card.straitsx.ai/production/sse"

# REST endpoint behind an x402 payment challenge (PRD Section 9.2 discovery finding:
# the MCP tool itself only returns payment requirements, the actual card issuance is
# this HTTP call, paid via a signed EIP-3009 TransferWithAuthorization).
STRAITSX_SANDBOX_CARDAPI = "https://card.straitsx.ai/sandbox/cardapi/issue_card"
STRAITSX_PRODUCTION_CARDAPI = "https://card.straitsx.ai/production/cardapi/issue_card"

# Wallet that signs the EIP-3009 TransferWithAuthorization paying the x402
# challenge returned by StraitsX's cardapi. For STRAITSX_PROFILE=production this must
# be a wallet actually holding real XSGD on Avalanche C-Chain — the sandbox wallet
# (funded with test XSGD on Fuji only) will just fail on-chain, not move real funds.
STRAITSX_WALLET_ADDRESS = os.getenv("STRAITSX_WALLET_ADDRESS", "")
STRAITSX_WALLET_PRIVATE_KEY = os.getenv("STRAITSX_WALLET_PRIVATE_KEY", "")

MIN_CARD_AMOUNT_SGD = 5.0
MAX_CARD_AMOUNT_SGD = 30.0

# Confirmed via live StraitsX responses, PRD Section 9.4. straitsx_client.py checks
# every x402 challenge's asset/chainId against these before signing, so a challenge
# pointing at the wrong network for the active profile gets rejected instead of
# silently paid.
XSGD_ADDRESS_SANDBOX = "0xd769410dc8772695a7f55a304d2125320a65c2a5"
XSGD_ADDRESS_PRODUCTION = "0xb2f85b7ab3c2b6f62df06de6ae7d09c010a5096e"
XSGD_CHAIN_ID_SANDBOX = 43113      # Avalanche Fuji
XSGD_CHAIN_ID_PRODUCTION = 43114   # Avalanche C-Chain Mainnet

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
