"""Seed catalogue. Prices held to 5-6.90 SGD (well under the 5-30 SGD card cap from PRD
Section 9.6) so a handful of real StraitsX test purchases fit inside a small sandbox
wallet balance without any single order eating the whole thing."""
from sqlmodel import Session, select

from app.models import Product

CATALOGUE = [
    ("SKU-1001", "Ceramic Pour-Over Coffee Dripper", "Single-origin coffee dripper, hand-glazed stoneware.", "home", 6.90),
    ("SKU-1002", "Braided Leather Bookmark", "Vegetable-tanned leather, brass tip.", "gifts", 5.20),
    ("SKU-1003", "Silicone Earbud Case Cover", "Silicone skin for compact earbud cases.", "electronics", 5.90),
    ("SKU-1004", "Pocket Notebook 3-Pack", "Set of 3 dot-grid notebooks, 96 pages each.", "stationery", 5.50),
    ("SKU-1005", "Enamel Camping Mug", "16oz enamel mug with birch handle.", "home", 5.90),
    ("SKU-1006", "Bluetooth Key Finder", "Coin-cell tracker tag, app-paired.", "electronics", 6.50),
    ("SKU-1007", "Cedarwood Scented Candle", "40hr burn, hand-poured soy wax.", "gifts", 5.90),
    ("SKU-1008", "Travel Cable Organizer Pouch", "Water-resistant pouch, 3 mesh compartments.", "electronics", 6.20),
    ("SKU-1009", "Botanical Birthday Card", "Letterpress card with kraft envelope.", "gifts", 5.00),
    ("SKU-1010", "Mini Succulent Planter Set", "Set of 3 ceramic planters, drainage hole.", "home", 6.90),
    ("SKU-1011", "Scrabble Board Game", "Fast-paced word game, 2-6 players.", "toys", 6.90),
    ("SKU-1012", "Insulated Travel Tumbler", "Double-wall stainless steel, leakproof lid.", "home", 6.50),
    ("SKU-1013", "USB-C Multiport Hub", "4-in-1 hub: HDMI, USB-A x2, USB-C PD.", "electronics", 6.90),
    ("SKU-1014", "City Skyline Jigsaw Puzzle", "500-piece jigsaw, matte finish.", "toys", 5.90),
    ("SKU-1015", "Handmade Soap Bar Set", "Oat, charcoal, and citrus bars.", "gifts", 5.50),
]


def seed_products(session: Session) -> None:
    existing = session.exec(select(Product)).first()
    if existing:
        return
    for sku, name, description, category, price in CATALOGUE:
        session.add(Product(sku=sku, name=name, description=description, category=category, price_sgd=price))
    session.commit()
