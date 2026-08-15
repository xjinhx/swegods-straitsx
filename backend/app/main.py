from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.config import CORS_ORIGINS, MERCHANT_NAME, MOCK_STRAITSX, STRAITSX_PROFILE
from app.database import create_db_and_tables, engine
from app.routers import audit, authorise, checkout, identify, merchant, products, receipt
from app.seed import seed_products


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        seed_products(session)
    yield


app = FastAPI(
    title=f"{MERCHANT_NAME} — Agent-Native Merchant API",
    description=(
        "Merchant API built for AI shopping agents as first-class customers. "
        "See PRD Section 7 for the full endpoint contract."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(identify.router)
app.include_router(checkout.router)
app.include_router(authorise.router)
app.include_router(receipt.router)
app.include_router(audit.router)
app.include_router(merchant.router)


@app.get("/")
def root():
    return {
        "merchant": MERCHANT_NAME,
        "status": "ok",
        "straitsx_mode": "mock" if MOCK_STRAITSX else "live",
        "straitsx_profile": STRAITSX_PROFILE,
        "docs": "/docs",
    }
