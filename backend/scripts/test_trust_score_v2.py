"""
trust-score-v2 demo script: drives the two scenarios that matter for the pitch —
a clean checkout and a tampered-price checkout — against a running backend, printing
the score_breakdown at each stage so the live_trust_score move is visible without
needing the frontend up.

Usage:
    # terminal 1
    cd backend && uvicorn app.main:app --port 8000

    # terminal 2
    cd backend && .venv/Scripts/python.exe scripts/test_trust_score_v2.py [sku]
"""
import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"
SKU = sys.argv[1] if len(sys.argv) > 1 else "SKU-1009"


def identify(client: httpx.Client, merchant: str, credential_suffix: str) -> dict:
    resp = client.post("/identify", json={
        "agent_name": "trust-v2-demo-agent",
        "credential": f"demo.script.credential-{credential_suffix}",
        "issuer": "demo-agent-v1",
        "mandate": {"spend_cap_sgd": 50, "merchant_whitelist": [merchant], "expiry_hours": 1},
    }).json()
    print(f"[identify] agent_id={resp['agent_id']} identify_trust_score={resp['trust']['trust_score']} "
          f"(identity={resp['trust']['identity_score']}, mandate={resp['trust']['mandate_scope_score']}, "
          f"behavior={resp['trust']['behavior_score']})")
    return resp


def print_breakdown(label: str, breakdown: dict | None):
    if not breakdown:
        print(f"  {label}: (no score_breakdown)")
        return
    parts = ", ".join(f"{k}={v}" for k, v in breakdown.items() if v is not None)
    print(f"  {label}: {parts}")


def scenario_clean(client: httpx.Client, merchant: str, price_sgd: float):
    print("\n=== Scenario 1: clean checkout (no price assertion) ===")
    ident = identify(client, merchant, "clean")
    session_token = ident["session_token"]

    checkout = client.post("/checkout", json={
        "session_token": session_token, "sku": SKU, "quantity": 1,
    }).json()
    print(f"[checkout] order_id={checkout['order_id']} status={checkout['status']} "
          f"live_trust_score={checkout['trust_score']} required={checkout['required_trust']} "
          f"denial_reason={checkout.get('denial_reason')}")
    print_breakdown("score_breakdown", checkout.get("score_breakdown"))

    if checkout["status"] != "approved":
        print("Order was not approved — nothing to authorise.")
        return

    resp = client.post("/authorise", json={"session_token": session_token, "order_id": checkout["order_id"]})
    if resp.status_code != 200:
        print(f"[authorise] FAILED — HTTP {resp.status_code}: {resp.text}")
        return
    auth = resp.json()
    print(f"[authorise] status={auth['status']} card_id={auth['card_id']}")
    print_breakdown("score_breakdown", auth.get("score_breakdown"))


def scenario_tampered(client: httpx.Client, merchant: str, price_sgd: float):
    print("\n=== Scenario 2: tampered checkout (asserted price far off catalog) ===")
    ident = identify(client, merchant, "tampered")
    session_token = ident["session_token"]

    fake_price = round(price_sgd * 0.5, 2)  # 50% off — well past the 5% gate
    checkout = client.post("/checkout", json={
        "session_token": session_token, "sku": SKU, "quantity": 1,
        "expected_price_sgd": fake_price,
    }).json()
    print(f"[checkout] asserted_price={fake_price} catalog_price={price_sgd}")
    print(f"[checkout] order_id={checkout['order_id']} status={checkout['status']} "
          f"live_trust_score={checkout['trust_score']} required={checkout['required_trust']} "
          f"reason={checkout.get('reason')} denial_reason={checkout.get('denial_reason')}")
    print_breakdown("score_breakdown", checkout.get("score_breakdown"))

    assert checkout["status"] == "blocked", "expected the tampered checkout to be blocked"
    assert checkout["denial_reason"] == "commercial_validity_failure"
    print("Confirmed: blocked at /checkout with denial_reason=commercial_validity_failure "
          "— a high identity/mandate score could not buy this back.")


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30)
    root = client.get("/").json()
    merchant = root["merchant"]
    print(f"Backend: {merchant} — straitsx_mode={root['straitsx_mode']} profile={root['straitsx_profile']}")

    products = client.get("/products").json()
    product = next(p for p in products if p["sku"] == SKU)
    price_sgd = product["price_sgd"]
    print(f"Target SKU: {SKU} — {product['name']} — ${price_sgd:.2f} SGD")

    scenario_clean(client, merchant, price_sgd)
    scenario_tampered(client, merchant, price_sgd)


if __name__ == "__main__":
    main()
