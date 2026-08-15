"""
Drives /identify -> /checkout -> /authorise against a running backend, so the
StraitsX card-issuance wiring (app/straitsx_client.py) can be exercised without
the Claude-powered demo agent or an ANTHROPIC_API_KEY.

Usage:
    # terminal 1
    cd backend && uvicorn app.main:app --reload --port 8000

    # terminal 2
    cd backend && .venv/Scripts/python.exe scripts/test_authorise_flow.py [sku]

Defaults to SKU-1009 (Birthday Card - Botanical, $5.50 SGD) — the cheapest seeded
product, to keep test authorisations small.
"""
import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"
SKU = sys.argv[1] if len(sys.argv) > 1 else "SKU-1009"


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30)

    root = client.get("/").json()
    print(f"Backend: {root['merchant']} - straitsx_mode={root['straitsx_mode']} "
          f"profile={root['straitsx_profile']}\n")

    identify = client.post("/identify", json={
        "agent_name": "test-script-agent",
        "credential": "test.script.credential-v1",
        "issuer": "test-script",
        "mandate": {"spend_cap_sgd": 50, "merchant_whitelist": [root["merchant"]], "expiry_hours": 1},
    }).json()
    print(f"[identify] agent_id={identify['agent_id']} trust_score={identify['trust']['trust_score']}")
    session_token = identify["session_token"]

    checkout = client.post("/checkout", json={
        "session_token": session_token, "sku": SKU, "quantity": 1,
    }).json()
    print(f"[checkout] order_id={checkout['order_id']} status={checkout['status']} "
          f"amount_sgd={checkout['amount_sgd']} reason={checkout.get('reason')}")

    if checkout["status"] != "approved":
        print("\nOrder was not approved - nothing to authorise. Exiting.")
        return

    resp = client.post("/authorise", json={
        "session_token": session_token, "order_id": checkout["order_id"],
    })
    if resp.status_code != 200:
        print(f"\n[authorise] FAILED - HTTP {resp.status_code}: {resp.text}")
        return

    authorise = resp.json()
    print(f"[authorise] status={authorise['status']} card_id={authorise['card_id']} "
          f"settlement_tx={authorise['settlement_tx']}")
    print(f"\nReceipt: {BASE_URL}{authorise['receipt_url']}")


if __name__ == "__main__":
    main()
