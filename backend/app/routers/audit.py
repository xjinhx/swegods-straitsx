"""GET /audit/{order_id} and GET /activity/feed — append-only audit trail (PRD Section
6 step 7, Milestone 6 "Prove"). /activity/feed backs both the agent demo view and the
merchant dashboard's live feed (Section 8.1) off the same underlying events."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.audit import event_to_dict
from app.database import get_session
from app.models import AuditEvent, Order

router = APIRouter(tags=["audit"])


@router.get("/audit/{order_id}")
def get_order_audit(order_id: str, session: Session = Depends(get_session)):
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    events = session.exec(
        select(AuditEvent).where(AuditEvent.order_id == order_id).order_by(AuditEvent.timestamp)
    ).all()
    return {
        "order_id": order_id,
        "status": order.status,
        "events": [event_to_dict(e) for e in events],
    }


@router.get("/activity/feed")
def activity_feed(limit: int = 50, session: Session = Depends(get_session)):
    events = session.exec(
        select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(min(limit, 200))
    ).all()
    return [event_to_dict(e) for e in events]
