"""Demo shopping agent.

A human types a natural-language request; Claude drives the purchase end to end by
calling AgentMart's HTTP API as tools: browse -> identify -> checkout -> authorise ->
receipt. Every call it makes is real (against the running backend, not simulated), so
the same run shows up live in the merchant dashboard's activity feed.

Usage:
    pip install -r requirements.txt
    cp .env.example .env   # set ANTHROPIC_API_KEY
    python agent.py "buy me a birthday gift under $50"
"""
import json
import os
import sys

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

# The mandate a human owner would have configured for this agent ahead of time
# (spend cap, merchant whitelist, expiry). The LLM never invents
# this — it's fixed config, same as a real agent runtime would load from its wallet.
AGENT_NAME = "birthday-shopper"
CREDENTIAL = os.getenv("AGENT_CREDENTIAL", "demo.agent.credential-signed-blob-v1")
ISSUER = "claude-agent-sdk"
MANDATE = {
    "spend_cap_sgd": float(os.getenv("AGENT_SPEND_CAP_SGD", "50")),
    "merchant_whitelist": ["AgentMart"],
    "expiry_hours": 1,
}

http = httpx.Client(base_url=BACKEND_URL, timeout=15)
session_state = {"session_token": None}


def step(label: str, detail: str = "") -> None:
    print(f"\n\033[36m[{label}]\033[0m {detail}")


def browse_products(category: str | None = None) -> dict:
    resp = http.get("/products", params={"category": category} if category else None)
    resp.raise_for_status()
    return {"products": resp.json()}


def identify() -> dict:
    resp = http.post("/identify", json={
        "agent_name": AGENT_NAME,
        "credential": CREDENTIAL,
        "issuer": ISSUER,
        "mandate": MANDATE,
    })
    resp.raise_for_status()
    data = resp.json()
    session_state["session_token"] = data["session_token"]
    return data


def checkout(sku: str, quantity: int = 1) -> dict:
    if not session_state["session_token"]:
        return {"error": "not identified yet — call identify first"}
    resp = http.post("/checkout", json={
        "session_token": session_state["session_token"], "sku": sku, "quantity": quantity,
    })
    resp.raise_for_status()
    return resp.json()


def authorise(order_id: str) -> dict:
    if not session_state["session_token"]:
        return {"error": "not identified yet — call identify first"}
    resp = http.post("/authorise", json={
        "session_token": session_state["session_token"], "order_id": order_id,
    })
    if resp.status_code >= 400:
        return {"error": resp.json().get("detail", resp.text)}
    return resp.json()


def get_receipt(order_id: str) -> dict:
    resp = http.get(f"/receipt/{order_id}")
    if resp.status_code >= 400:
        return {"error": resp.json().get("detail", resp.text)}
    return resp.json()


TOOL_IMPL = {
    "browse_products": browse_products,
    "identify": identify,
    "checkout": checkout,
    "authorise": authorise,
    "get_receipt": get_receipt,
}

TOOLS = [
    {
        "name": "browse_products",
        "description": "List the merchant's catalogue, optionally filtered by category.",
        "input_schema": {
            "type": "object",
            "properties": {"category": {"type": "string", "description": "optional category filter"}},
        },
    },
    {
        "name": "identify",
        "description": (
            "Present your signed mandate credential to the merchant so it can verify "
            "you and compute a trust score. Call this once before checkout."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "checkout",
        "description": "Request to buy a specific SKU. Returns whether the merchant approved or blocked it, and an order_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sku": {"type": "string"},
                "quantity": {"type": "integer", "default": 1},
            },
            "required": ["sku"],
        },
    },
    {
        "name": "authorise",
        "description": "Settle payment for an approved order via the merchant's card gateway. Only works if checkout was approved.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "get_receipt",
        "description": "Fetch the signed, tamper-evident receipt for a completed order.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
]

SYSTEM_PROMPT = f"""You are a shopping agent acting on behalf of a human, buying from
the AgentMart merchant API. You have a mandate with a spend cap of
{MANDATE['spend_cap_sgd']} SGD and are only authorised to shop at AgentMart.

Follow this order: identify yourself first, browse the catalogue, pick ONE product
that best satisfies the human's request and fits the budget, checkout, then authorise
payment, then fetch the receipt as proof.

If checkout comes back "blocked", do not retry the same purchase — explain plainly to
the human why it was blocked (trust score, spend cap, or a merchant rule) and stop;
only a human merchant can override a block, you cannot. Keep your narration brief —
one or two sentences per step, not a running commentary."""


def run(prompt: str) -> None:
    client = Anthropic()
    messages = [{"role": "user", "content": prompt}]

    step("HUMAN", prompt)

    for _ in range(12):  # hard stop so a stuck loop can't run forever
        response = client.messages.create(
            model=MODEL, max_tokens=1024, system=SYSTEM_PROMPT, tools=TOOLS, messages=messages,
        )

        text_parts = [b.text for b in response.content if b.type == "text" and b.text.strip()]
        if text_parts:
            step("AGENT", " ".join(text_parts))

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for call in tool_uses:
            step(call.name.upper(), json.dumps(call.input))
            result = TOOL_IMPL[call.name](**call.input)
            print(json.dumps(result, indent=2, default=str)[:800])
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(result, default=str),
            })
        messages.append({"role": "user", "content": tool_results})

        if response.stop_reason != "tool_use":
            break


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY (see .env.example).", file=sys.stderr)
        sys.exit(1)
    user_prompt = " ".join(sys.argv[1:]) or "buy me a birthday gift under $50"
    run(user_prompt)
