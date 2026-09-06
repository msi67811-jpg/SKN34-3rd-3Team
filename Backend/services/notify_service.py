from datetime import datetime
from email.message import EmailMessage
import smtplib

from core import store
from core.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from core.database import persist


def list_notifications(user_id: int) -> list[dict]:
    dispatch_due_reminders()
    rows = [item for item in store.notifications.values() if item["user_id"] == user_id]
    rows.sort(key=lambda item: item["created_at"], reverse=True)
    return [_to_item(item) for item in rows]


def unread_count(user_id: int) -> int:
    return sum(
        1
        for item in store.notifications.values()
        if item["user_id"] == user_id and not item.get("read")
    )


def mark_read(user_id: int, notification_id: int | None = None) -> None:
    for item in store.notifications.values():
        if item["user_id"] != user_id:
            continue
        if notification_id is None or item["id"] == notification_id:
            item["read"] = True
    persist()


def dispatch_due_reminders() -> int:
    created = 0
    now = datetime.now()
    for reminder in list(store.reminders.values()):
        if reminder.get("dispatched"):
            continue
        notify_at = reminder.get("notify_at")
        if isinstance(notify_at, str):
            notify_at = datetime.fromisoformat(notify_at)
        if not notify_at or notify_at > now:
            continue
        event = store.calendar_events.get(reminder["event_id"])
        if not event:
            continue
        user = store.users.get(reminder["user_id"]) or {}
        title = f"일정 알림: {event['title']}"
        body = f"{event['title']} 마감은 {event['due_date']}입니다. 앱에서 일정을 확인하세요."
        phone = (user.get("phone") or "").strip()
        _create_notification(reminder["user_id"], "reminder", title, body, "in_app")
        _create_notification(reminder["user_id"], "push", title, body, "push")
        email_status = _send_email(user.get("email") or "", title, body)
        _create_notification(
            reminder["user_id"],
            "email",
            title,
            body,
            "email",
            email_status,
        )
        sms_status = _queue_sms(phone, f"{title} {body}")
        _create_notification(
            reminder["user_id"],
            "sms",
            title,
            f"{phone or '번호 없음'} · {body}" if phone else "휴대폰 번호가 없어 문자는 보내지 않았습니다.",
            "sms",
            sms_status,
        )
        reminder["dispatched"] = True
        created += 1
    if created:
        persist()
    return created


def notify_now(user_id: int, event_id: int) -> dict:
    event = store.calendar_events.get(event_id)
    if not event:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    title = f"일정 알림: {event['title']}"
    body = f"{event['title']} 마감은 {event['due_date']}입니다."
    user = store.users.get(user_id) or {}
    in_app = _create_notification(user_id, "push", title, body, "push")
    email_status = _send_email(user.get("email") or "", title, body)
    _create_notification(user_id, "email", title, body, "email", email_status)
    persist()
    return {"notificationId": in_app, "emailStatus": email_status}


def _create_notification(
    user_id: int,
    kind: str,
    title: str,
    body: str,
    channel: str,
    status: str = "delivered",
) -> int:
    nid = store.next_id("notification")
    store.notifications[nid] = {
        "id": nid,
        "user_id": user_id,
        "kind": kind,
        "title": title,
        "body": body,
        "channel": channel,
        "status": status,
        "read": False,
        "created_at": datetime.now(),
    }
    return nid


def _send_email(to_email: str, subject: str, body: str) -> str:
    if not to_email:
        return "skipped"
    if not SMTP_HOST:
        return "queued-local"
    try:
        message = EmailMessage()
        message["From"] = SMTP_FROM
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as smtp:
            smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
        return "sent"
    except Exception:
        return "failed"


def _queue_sms(phone: str, text: str) -> str:
    if not phone:
        return "skipped"
    return "queued-local"


def _to_item(item: dict) -> dict:
    return {
        "id": item["id"],
        "kind": item["kind"],
        "title": item["title"],
        "body": item["body"],
        "channel": item["channel"],
        "status": item["status"],
        "read": bool(item.get("read")),
        "createdAt": item["created_at"],
    }
