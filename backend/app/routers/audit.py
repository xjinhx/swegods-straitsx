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
def activity_feed(
    limit: int = 50,
    since_id: int | None = None,
    before_id: int | None = None,
    session: Session = Depends(get_session),
):
    """Always returns newest-first. Cursors are mutually exclusive:
      - since_id: events after this id — the dashboard's poll uses this to fetch only
        what's new since its last-seen event and prepend, instead of re-fetching (and
        re-rendering) the same top-N window every 2s.
      - before_id: events before this id — "load older" when the feed's scroll region
        is paged back, so history beyond the initial window is still reachable instead
        of being clipped off by the fixed-height scroll container.
    `id` (not timestamp) is the cursor: AuditEvent.id is an autoincrementing PK assigned
    in insertion order, which already matches chronological order (log_event always
    writes in real time) — a strictly-increasing integer sidesteps the tie-breaking a
    millisecond-resolution timestamp cursor would need under concurrent writes.

    has_more is only meaningful for before_id (is there older history beyond this page)
    and since_id (did more than `limit` events land between two polls, i.e. a burst the
    client should know it might not have fully caught up on) — always false for a bare,
    cursor-less fetch.
    """
    if since_id is not None and before_id is not None:
        raise HTTPException(status_code=400, detail="pass only one of since_id or before_id")

    capped_limit = min(limit, 200)
    query = select(AuditEvent)
    if since_id is not None:
        query = query.where(AuditEvent.id > since_id)
    elif before_id is not None:
        query = query.where(AuditEvent.id < before_id)

    # Fetch one extra row to know whether more exist beyond this page, without a
    # separate COUNT query.
    rows = session.exec(query.order_by(AuditEvent.id.desc()).limit(capped_limit + 1)).all()
    has_more = len(rows) > capped_limit
    return {"events": [event_to_dict(e) for e in rows[:capped_limit]], "has_more": has_more}
