from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Product
from app.schemas import ProductOut

router = APIRouter(tags=["catalogue"])


@router.get("/products", response_model=list[ProductOut])
def list_products(category: str | None = None, session: Session = Depends(get_session)):
    query = select(Product)
    if category:
        query = query.where(Product.category == category)
    return session.exec(query).all()


@router.get("/products/{sku}", response_model=ProductOut)
def get_product(sku: str, session: Session = Depends(get_session)):
    product = session.get(Product, sku)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    return product
