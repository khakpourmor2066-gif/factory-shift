from sqlalchemy.orm import Session

from app.modules.webhook_logs.model import WebhookLog


def create_webhook_log(
    db: Session,
    *,
    platform: str,
    messenger_user_id: str,
    direction: str,
    event_type: str,
    request_text: str | None = None,
    response_status: str | None = None,
    response_text: str | None = None,
    sent_status: bool = False,
) -> WebhookLog:
    log = WebhookLog(
        platform=platform,
        messenger_user_id=messenger_user_id,
        direction=direction,
        event_type=event_type,
        request_text=request_text,
        response_status=response_status,
        response_text=response_text,
        sent_status=sent_status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_webhook_log_report(db: Session) -> dict:
    rows = db.query(WebhookLog).all()
    counts = {
        "incoming": 0,
        "outgoing": 0,
        "sent": 0,
        "failed": 0,
    }
    for row in rows:
        if row.direction in counts:
            counts[row.direction] += 1
        if row.sent_status:
            counts["sent"] += 1
        else:
            counts["failed"] += 1
    latest = sorted(rows, key=lambda row: row.created_at, reverse=True)[:10]
    return {"counts": counts, "total": len(rows), "latest": latest}
