"""
One-time setup: generates the Ed25519 keypair AgentMart (the issuer) uses to sign
session tokens and receipts (app/security.py). Run once per environment; the private
key must never be committed (see .gitignore).

Usage:
    cd backend && .venv/Scripts/python.exe scripts/generate_issuer_keypair.py
"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)

with open("issuer_private_key.pem", "wb") as f:
    f.write(private_pem)
with open("issuer_public_key.pem", "wb") as f:
    f.write(public_pem)

print("Generated issuer_private_key.pem and issuer_public_key.pem in the current directory.")
print("Confirm issuer_private_key.pem is gitignored before committing anything.")
