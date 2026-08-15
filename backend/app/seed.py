"""Seed catalogue. Prices held to 5-30 SGD per PRD Section 9.6 (card cap constraint)."""
from sqlmodel import Session, select

from app.models import Product

CATALOGUE = [
    ("SKU-1001", "Ceramic Pour-Over Dripper", "Single-origin coffee dripper, hand-glazed stoneware.", "home", 24.90),
    ("SKU-1002", "Braided Leather Bookmark", "Vegetable-tanned leather, brass tip.", "gifts", 8.50),
    ("SKU-1003", "Wireless Earbud Case Skin", "Silicone skin for compact earbud cases.", "electronics", 6.90),
    ("SKU-1004", "Pocket Notebook Trio", "Set of 3 dot-grid notebooks, 96 pages each.", "stationery", 11.00),
    ("SKU-1005", "Enamel Camp Mug", "16oz enamel mug with birch handle.", "home", 9.90),
    ("SKU-1006", "Bluetooth Keyfinder Tag", "Coin-cell tracker tag, app-paired.", "electronics", 17.50),
    ("SKU-1007", "Scented Soy Candle - Cedar", "40hr burn, hand-poured soy wax.", "gifts", 14.90),
    ("SKU-1008", "Travel Cable Organiser Pouch", "Water-resistant pouch, 3 mesh compartments.", "electronics", 13.20),
    ("SKU-1009", "Birthday Card - Botanical", "Letterpress card with kraft envelope.", "gifts", 5.50),
    ("SKU-1010", "Mini Succulent Planter Set", "Set of 3 ceramic planters, drainage hole.", "home", 19.90),
    ("SKU-1011", "Board Game - Word Sprint", "Fast-paced word game, 2-6 players.", "toys", 27.00),
    ("SKU-1012", "Insulated Tumbler 500ml", "Double-wall stainless steel, leakproof lid.", "home", 22.00),
    ("SKU-1013", "USB-C Multiport Adapter", "4-in-1 hub: HDMI, USB-A x2, USB-C PD.", "electronics", 29.90),
    ("SKU-1014", "Puzzle - City Skyline 500pc", "500-piece jigsaw, matte finish.", "toys", 16.40),
    ("SKU-1015", "Handmade Soap Trio", "Oat, charcoal, and citrus bars.", "gifts", 12.30),
]


def seed_products(session: Session) -> None:
    existing = session.exec(select(Product)).first()
    if existing:
        return
    for sku, name, description, category, price in CATALOGUE:
        session.add(Product(sku=sku, name=name, description=description, category=category, price_sgd=price))
    session.commit()
