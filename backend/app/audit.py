import json

from sqlmodel import Session

from app.models import AuditEvent


def log_event(
    session: Session,
    step: str,
    message: str,
    order_id: str | None = None,
    agent_id: str | None = None,
    detail: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        order_id=order_id,
        agent_id=agent_id,
        step=step,
        message=message,
        detail_json=json.dumps(detail or {}),
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def event_to_dict(event: AuditEvent) -> dict:
    return {
        "id": event.id,
        "order_id": event.order_id,
        "agent_id": event.agent_id,
        "step": event.step,
        "message": event.message,
        "detail": json.loads(event.detail_json),
        "timestamp": event.timestamp.isoformat() + "Z",
    }
