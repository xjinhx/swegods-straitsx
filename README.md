# AgentMart

An AI agent just showed up to buy something. It has no face, no history with you, and nobody standing behind it to check its ID. Do you sell to it? AgentMart is a merchant built to answer that question in real time, not dodge it: there's no login form and no checkout button, because there's no human on the other end. An agent presents credentials, gets back a live, five-factor trust score, and the merchant's own configurable rules decide, in real time, whether the purchase goes through. Every purchase that clears settles in real $XSGD on Avalanche C-Chain mainnet.

![AgentMart system architecture: a human prompts a Claude agent, which calls the AgentMart API for trust scoring, merchant rules, and the identify/checkout/authorise/receipt flow; the API authorises through the StraitsX card API using the x402 challenge protocol and an EIP-3009 signed transfer, which settles on-chain in XSGD on Avalanche C-Chain; every step is logged to an append-only audit log, which updates the merchant dashboard, and a human can override a blocked order from that dashboard.](AgentMart_Diagram3.png)

## Why AgentMart: AI-native Commerce (Track 3)

Agent-driven commerce isn't a 2030 forecast — it's 120 million agent-initiated payments on Alipay's AI Pay in a single week this February, and in Singapore, 8 in 10 shoppers already lean on AI when they buy something online. That volume is already arriving at merchants' doors, and nearly all of the industry's response so far has been built for the agent's side of the counter: how it spends safely. Almost nothing has been built for the merchant's side — how to decide whether to sell to a customer with no face, no history, and nothing to check at the door. That's the gap Track 3 names directly: "the merchant experiences, APIs, and protocols for a future where AI agents become first-class customers." AgentMart answers that literally: it's the merchant side of that future, built so an agent is a first-class customer with its own trust profile the merchant evaluates, not a human pretending to click buttons, and not a checkout that always says yes.

**Five value propositions:**

1. **Trust is a live number the merchant reads, not a login gate the agent passes once.** StraitsX's own deck names the gap plainly: a scoped credential limits what a compromised agent can spend, but "does not make the agent trustworthy, that part is still open." That's the merchant's problem to solve, not the wallet's — and it's what AgentMart actually does. Identity and mandate are frozen at `/identify`, but behavior, commercial validity, and payment authority are recomputed fresh at `/checkout` and `/authorise`. Nothing coasts on a good first impression.

2. **Price-injection defense is built into checkout.** `/checkout` compares what the agent *believes* it's paying against the live catalog price. If a poisoned product page fed the agent a fake price, the mismatch hard-blocks the order regardless of how trustworthy the agent otherwise looks (see Test Case 3). This closes a specific, demonstrated attack surface in agentic commerce, not just a generic fraud check.

3. **Reputation is earned, not asserted.** `behavior_score` uses a Wilson-score-interval lower bound over an agent's own resolved order history, the same statistic Reddit uses to rank comments, so one lucky order can't buy a perfect trust score, and merchant-assisted overrides count as a trial but not a clean success.

4. **Merchant policy is configuration, not code.** Category caps, price thresholds, and blocked categories are written live from the dashboard's rule builder and read live by `/checkout` on the very next request: a merchant reconfigures risk tolerance without a redeploy.

5. **StraitsX only gets called once trust already cleared, and even then we check it's talking to the right network.** A bad-credential or price-mismatch order never reaches `/authorise` at all, the trust engine blocks it first (see Test Cases 1 and 2, no StraitsX call is ever made). When a payment does authorize, the challenge's asset address and chain id are cross-checked against the active network before anything gets signed, so a misdirected challenge gets rejected instead of silently signed. And the receipts themselves are real artifacts, not just database rows: session tokens and receipts are signed with a real Ed25519 keypair, verifiable by anyone with the public key, and a cleared payment settles as an actual transaction checkable on Snowtrace.

And the demo agent itself is real too: Claude actually decides what to buy, no scripted flow behind the scenes.

## The merchant's dashboard

Everything above works over the API, but a merchant shouldn't have to trust a black box with real money. The dashboard is the same trust scores, rules, and decisions, made visible and watchable live, not buried in a response body.

- **Live activity feed** — every identify/checkout/block/authorise/override/revoke event, polling in real time, cursor-paginated so it never re-renders the whole feed on every tick.
- **Rule builder** — `category_cap`, `price_threshold`, `blocked_category` rules, written live and read by `/checkout` on the very next request: a merchant reconfigures risk tolerance without a redeploy.
- **Per-agent trust panel + trust trajectory chart** — the five-factor breakdown and how it moved over an agent's history, not just the current number.
- **Order timeline + per-order audit trail** (`GET /audit/{order_id}`) — every scoring decision that led to an approve/block, with the reasoning, not just the outcome. `blocked` needs a merchant override before the agent may retry `/authorise` at all; a `failed` authorization (StraitsX itself rejected the charge) is tracked as a distinct state, so an infra hiccup on their end is never held against the agent's reputation.
- **Manual override** for blocked orders, and **instant credential revoke/reinstate** for an agent mid-session.

## Live demo

- Frontend (Vercel): https://swegods-straitsx.vercel.app
- Backend API (Railway): https://swegods-straitsx-production.up.railway.app
- Interactive API docs: https://swegods-straitsx-production.up.railway.app/docs

## What this actually is

Three pieces, each runnable and deployable on its own:

| Piece | What it is | Where it lives |
|---|---|---|
| `backend/` | FastAPI + SQLite merchant API: products, identify, checkout, authorise, receipt, audit, merchant dashboard endpoints | Deployed on Railway |
| `frontend/` | Vue 3 app: the agent demo view and the merchant dashboard, both polling the backend live | Deployed on Vercel |
| `demo_agent/` | A Claude-powered shopping agent, a CLI script that calls the backend over HTTP the same way any other agent would | Runs locally |

## How an agent uses it

1. `GET /products`: browse the catalogue.
2. `POST /identify`: present a credential (a mandate: spend cap, merchant whitelist, expiry). Identity is derived from the credential's own hash, so repeat calls with the same credential resolve to the same agent record, which is what makes velocity and reputation signals meaningful over time instead of resetting every call. Returns a signed session token and a trust breakdown.
3. `POST /checkout`: attempt to buy a SKU. The merchant's live rule engine approves or blocks based on the current trust score.
4. `POST /authorise`: real payment settlement through StraitsX (x402 challenge, EIP-3009 signed transfer, real XSGD).
5. `GET /receipt/{order_id}`: a signed JWT as tamper-evident proof of purchase.

### The trust score: five factors, recomputed live at every stage

| Factor | What it measures | Frozen or live |
|---|---|---|
| `identity_score` | Credential signature validity + issuer reputation | Frozen at `/identify` |
| `mandate_scope_score` | Tighter spend cap / narrower whitelist / shorter expiry = higher trust | Frozen at `/identify` |
| `behavior_score` | Identify-request velocity, blended with Wilson-score reputation once the agent has order history | Live, recomputed every stage |
| `commercial_validity_score` | Does the agent's believed price match the live catalog? | Live at `/checkout`, carried into `/authorise` |
| `payment_authority_score` | Did StraitsX actually settle? | Live at `/authorise` only |

The blend weights shift by stage: `/identify` only has identity + mandate to work with; `/checkout` adds live behavior + commercial validity; `/authorise` adds payment authority once settlement succeeds. Two components are hard gates, not just weighted inputs: `identity_score < 50` or `commercial_validity_score < 50` blocks the checkout outright, no matter how high the blended score would otherwise be. Full detail in `backend/app/trust.py`.

## Try it yourself: test cases

These run against the live Railway backend via `demo_agent/`. Cases 1–4 are free: they all get blocked at `/checkout`, before StraitsX is ever called. Case 5 is the real thing and settles actual XSGD.

**1. Bad credential → identity gate blocks it**
```bash
AGENT_CREDENTIAL=short python agent.py "buy me a birthday gift under $50"
```
Fails the signed-shape check → `identity_score=20`, below the `IDENTITY_GATE` (50) → blocked, `denial_reason: identity_verification_failure`.

**2. Spend cap exceeded → blocked before payment**
```bash
AGENT_SPEND_CAP_SGD=10 python agent.py "buy me the USB-C multiport hub"
```
Item is 24.90 SGD against a 10 SGD cap → blocked, reason cites the exact cap exceeded. No StraitsX call is ever made.

**3. Price tampering / prompt-injection defense**
The demo agent's tool schema doesn't expose a price override to the LLM on purpose. This simulates an agent that had one injected anyway (e.g. from a poisoned product page):
```bash
BACKEND=https://swegods-straitsx-production.up.railway.app

TOKEN=$(curl -s -X POST "$BACKEND/identify" -H 'content-type: application/json' -d '{
  "agent_name": "price-tamper-test", "credential": "demo.agent.credential-signed-blob-v1",
  "issuer": "claude-agent-sdk",
  "mandate": {"spend_cap_sgd": 50, "merchant_whitelist": ["AgentMart"], "expiry_hours": 1}
}' | python -c "import sys,json;print(json.load(sys.stdin)['session_token'])")

curl -s -X POST "$BACKEND/checkout" -H 'content-type: application/json' -d "{
  \"session_token\": \"$TOKEN\", \"sku\": \"SKU-1013\", \"quantity\": 1, \"expected_price_sgd\": 1.00
}"
```
Agent asserts 1 SGD for a 24.90 SGD item → `commercial_validity_score=20` → hard-blocked regardless of trust score, `denial_reason: commercial_validity_failure`. (PowerShell: use `Invoke-RestMethod` with the same JSON bodies.)

**4. Merchant whitelist violation**
Same shape as case 3, but with `"merchant_whitelist": ["SomeOtherStore"]` in the mandate. `/checkout` 403s immediately, before any scoring runs at all.

**5. Happy path: real settlement**
```bash
python agent.py "get me a small home decor gift under $10"
```
Cheap item, everything passes, `/authorise` actually signs and settles on Avalanche mainnet. Fetch the receipt afterward with `GET /receipt/{order_id}`: a signed JWT carrying the real `settlement_tx`, checkable on Snowtrace.

Reset any env overrides between runs (`unset AGENT_CREDENTIAL AGENT_SPEND_CAP_SGD`) so they don't bleed into the next one.

## Running it locally

Three terminals.

**1. Backend**
```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate on mac/linux
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
Docs at http://127.0.0.1:8000/docs. Seeds a 15 product catalogue (5 to 30 SGD, matching StraitsX's card cap) on first run.

**2. Frontend**
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. Two views: Agent view (live flow and catalogue) and Merchant dashboard (activity feed, trust breakdown, orders, rule builder).

**3. Demo agent**
```bash
cd demo_agent
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # set ANTHROPIC_API_KEY
python agent.py 'buy me a birthday gift under $50'
```
Use single quotes around the prompt, not double quotes. In bash, `"$50"` gets read as the variable `$5` followed by a literal `0`, which silently turns your budget into zero. Single quotes never expand anything, so they are safe in both bash and PowerShell.

Watch the frontend update live as it runs: identify, then checkout, then authorise, then receipt, each step a real call against the backend.

## Deployment

### Frontend, on Vercel

The frontend is a static Vite build. Because this is a monorepo (backend and frontend live in the same repo), Vercel needs a `vercel.json` at the repo root telling it this is a multi service project and how to route requests to the frontend:

```json
{
    "services": {
        "frontend": {
            "root": "frontend",
            "framework": "vite"
        }
    },
    "rewrites": [
        {
            "source": "/(.*)",
            "destination": {
                "type": "service",
                "service": "frontend"
            }
        }
    ]
}
```

The `rewrites` block matters: without it, the service builds fine but nothing is actually mounted at any path, and every request 404s.

Environment variable needed on Vercel:

| Variable | Value |
|---|---|
| `VITE_BACKEND_URL` | The deployed backend URL, no trailing slash |
| `VITE_MERCHANT_API_KEY` | Only needed if `MERCHANT_API_KEY` is set on the backend — must match it exactly |

Vite bakes environment variables in at build time, so changing this variable requires a redeploy, not just a save.

### Backend, on Railway

The backend needs a real, persistent host, not a serverless platform. It keeps a SQLite database file and two Ed25519 key files on disk, and it holds a wallet private key that can sign real transactions, so it needs a persistent volume rather than an ephemeral filesystem.

Setup:

1. New project, deploy from the GitHub repo, root directory set to `backend`.
2. Add a volume mounted at `/data`.
3. Environment variables:

| Variable | Value |
|---|---|
| `MERCHANT_NAME` | `AgentMart` |
| `DATABASE_URL` | `sqlite:////data/agentmart.db` (four slashes, not a typo) |
| `ISSUER_PRIVATE_KEY_PATH` | `/data/issuer_private_key.pem` |
| `ISSUER_PUBLIC_KEY_PATH` | `/data/issuer_public_key.pem` |
| `MOCK_STRAITSX` | `true` or `false` |
| `STRAITSX_PROFILE` | `sandbox` or `production` |
| `STRAITSX_WALLET_ADDRESS` | wallet address holding XSGD |
| `STRAITSX_WALLET_PRIVATE_KEY` | matching private key |
| `CORS_ORIGINS` | comma separated origins, including the Vercel domain, no spaces after the commas |
| `MERCHANT_API_KEY` | optional — gates `/merchant/*` (revoke, override, rule builder) behind a shared key; unset leaves it open, matching pre-gate behavior. Set it here and as `VITE_MERCHANT_API_KEY` on Vercel to turn it on |

4. Start command, already set in `backend/railway.json`:
   ```
   python scripts/ensure_issuer_keypair.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
   The keypair script only generates a new Ed25519 keypair if one is not already sitting on the volume, so redeploys do not rotate keys and invalidate every session token and receipt already issued.

## StraitsX integration status

The real integration is fully wired, not mocked-with-a-TODO: `/authorise` calls StraitsX's card-issuing MCP server over SSE (`get_card_sandbox` / `get_card_prod`), which hands back a cardapi URL and body; POSTing that triggers an x402 402 payment challenge; the backend signs an EIP-3009 `TransferWithAuthorization` for the exact requested amount and retries with a `PAYMENT-SIGNATURE` header; StraitsX returns the card and the on-chain `settlement_tx`. See `backend/app/straitsx_client.py`.

`MOCK_STRAITSX` and `STRAITSX_PROFILE` (both set per environment) control what actually happens:

- `MOCK_STRAITSX=true`: no network calls, a fake card and settlement hash are generated locally so the rest of the platform never blocks on gateway access.
- `STRAITSX_PROFILE=sandbox`: Avalanche Fuji testnet, chain id 43113, test XSGD, no real value at risk.
- `STRAITSX_PROFILE=production`: Avalanche C-Chain mainnet, chain id 43114, real XSGD. `_sign_payment` cross-checks every x402 challenge's asset address and chain id against the active profile's expected values before signing anything, so a challenge pointing at the wrong network gets rejected instead of silently signed.

The hackathon requirement is that the judged submission settles in real XSGD on mainnet. This deployment runs with `MOCK_STRAITSX=false` and `STRAITSX_PROFILE=production` against a wallet actually funded with mainnet XSGD.

## Research Foundations

Three design decisions in AgentMart are grounded in ideas from current agentic-commerce research, adapted into a working system rather than left as theory.

- **The merchant needs to own the purchase decision, not just verify identity.** Most e-commerce risk systems are built around scoring a transaction dynamically rather than relying on a one-time identity check, precisely because a static gate can't account for how risk shifts transaction to transaction (Lakkaraju, 2025). `backend/app/rules.py` is that dynamic layer for agentic checkout: `/checkout` reads live from merchant-authored `MerchantRule` rows instead of hardcoded thresholds, so the decision is explicit, inspectable, and owned by the merchant, not baked into a protocol nobody controls.

- **Trust should be a continuous, risk-adjusted score, not a pass/fail check.** Reputation research has long treated trust as an accumulated, probabilistic signal rather than a binary verified/unverified flag, since a hard cutoff treats every actor above the bar as equally trustworthy regardless of how much evidence actually backs that trust (Jøsang et al., 2007). `backend/app/trust.py` implements a five-factor weighted blend, recomputed live at each pipeline stage, with the full breakdown exposed on every API response and the dashboard, so trust is graded, not gated.

- **Identity needs to persist across sessions to mean anything.** A foundational result in reputation systems is that if an identity can be cheaply discarded and recreated, the reputation attached to it is worthless, the classic Sybil attack (Douceur, 2002). Agent identity in `backend/app/routers/identify.py` is derived from the credential's own hash, so repeat `/identify` calls resolve to the same agent record, the precondition for velocity and reputation signals to actually accumulate.

**References**

Douceur, J. R. (2002). The Sybil attack. In P. Druschel, F. Kaashoek, & A. Rowstron (Eds.), *Peer-to-peer systems: First international workshop, IPTPS 2002* (pp. 251–260). Springer. https://doi.org/10.1007/3-540-45748-8_24

Jøsang, A., Ismail, R., & Boyd, C. (2007). A survey of trust and reputation systems for online service provision. *Decision Support Systems*, *43*(2), 618–644. https://doi.org/10.1016/j.dss.2005.05.019

Lakkaraju, S. (2025). AI-powered dynamic risk scoring for e-commerce transactions. *International Journal of Scientific Research in Computer Science, Engineering and Information Technology*, *11*(1), 3515–3526. https://doi.org/10.32628/CSEIT251112363