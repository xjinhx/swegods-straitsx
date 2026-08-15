"""GET /receipt/{order_id} — PRD Section 6 step 7, Milestone 6 ("Prove")."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models import Order
from app.schemas import ReceiptOut
from app.security import verify_receipt

router = APIRouter(tags=["receipt"])


@router.get("/receipt/{order_id}", response_model=ReceiptOut)
def get_receipt(order_id: str, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order or not order.receipt_token:
        raise HTTPException(status_code=404, detail="no receipt for this order yet")

    claims = verify_receipt(order.receipt_token)  # tamper check: re-verifies the signature
    issued_at = datetime.fromtimestamp(claims["iat"], tz=timezone.utc).isoformat()
    return ReceiptOut(
        order_id=order.order_id,
        signed_receipt=order.receipt_token,
        agent_id=order.agent_id,
        sku=order.sku,
        amount_sgd=order.amount_sgd,
        settlement_tx=order.settlement_tx,
        issued_at=issued_at,
    )
