from datetime import datetime

from fastapi import HTTPException

from core import store


def _to_item(event: dict) -> dict:
    return {
        "id": event["id"],
        "eventType": event["event_type"],
        "title": event["title"],
        "dueDate": event["due_date"],
        "description": event["description"],
        "policyId": event.get("policy_id"),
    }


def list_events(year: int | None, month: int | None, event_type: str | None = None) -> list[dict]:
    rows = list(store.calendar_events.values())
    if event_type:
        rows = [e for e in rows if e["event_type"].lower() == event_type.lower()]
    if year:
        rows = [e for e in rows if e["due_date"].year == year]
    if month:
        rows = [e for e in rows if e["due_date"].month == month]
    rows.sort(key=lambda e: e["due_date"])
    return [_to_item(e) for e in rows]


def list_reminders(user_id: int) -> list[dict]:
    items = []
    for reminder in store.reminders.values():
        if reminder["user_id"] != user_id:
            continue
        event = store.calendar_events.get(reminder["event_id"])
        if not event:
            continue
        items.append(
            {
                "reminderId": reminder["id"],
                "eventId": reminder["event_id"],
                "title": event["title"],
                "dueDate": event["due_date"],
                "notifyAt": reminder["notify_at"],
            }
        )
    return items


def create_reminder(user_id: int, event_id: int, notify_at: datetime) -> int:
    if event_id not in store.calendar_events:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    rid = store.next_id("reminder")
    store.reminders[rid] = {
        "id": rid,
        "user_id": user_id,
        "event_id": event_id,
        "notify_at": notify_at,
        "created_at": datetime.now(),
    }
    return rid


def delete_reminder(user_id: int, reminder_id: int) -> None:
    reminder = store.reminders.get(reminder_id)
    if not reminder or reminder["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="리마인더를 찾을 수 없습니다.")
    del store.reminders[reminder_id]
