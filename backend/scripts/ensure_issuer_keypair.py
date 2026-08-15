"""
Idempotent issuer keypair generation for hosted deploys (Railway, Render, etc).
Unlike generate_issuer_keypair.py (local one-time setup, always overwrites), this
only generates a keypair if one isn't already present at the configured paths --
safe to run on every deploy. Point ISSUER_PRIVATE_KEY_PATH/ISSUER_PUBLIC_KEY_PATH at
a persistent volume so a redeploy doesn't rotate keys and invalidate every session
token/receipt already signed (app/security.py loads the same paths at import time).

Usage (run once per container start, before the app starts, from backend/):
    python scripts/ensure_issuer_keypair.py
"""
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

private_path = os.getenv("ISSUER_PRIVATE_KEY_PATH", "./issuer_private_key.pem")
public_path = os.getenv("ISSUER_PUBLIC_KEY_PATH", "./issuer_public_key.pem")

if os.path.exists(private_path) and os.path.exists(public_path):
    print(f"Issuer keypair already present at {private_path}, skipping.")
else:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    os.makedirs(os.path.dirname(private_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(public_path) or ".", exist_ok=True)

    with open(private_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(public_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    print(f"Generated new issuer keypair at {private_path} / {public_path}.")
