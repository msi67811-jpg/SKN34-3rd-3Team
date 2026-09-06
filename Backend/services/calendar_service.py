from datetime import date, datetime

from fastapi import HTTPException

from core import store
from core.database import persist
from services.policy_service import recommendations


def _to_item(event: dict, user_id: int | None = None) -> dict:
    return {
        "id": event["id"],
        "eventType": event["event_type"],
        "title": event["title"],
        "dueDate": event["due_date"],
        "description": event["description"] or "",
        "policyId": event.get("policy_id"),
        "mine": event["event_type"] == "USER" and event.get("user_id") == user_id,
    }


def list_events(
    year: int | None,
    month: int | None,
    event_type: str | None = None,
    user_id: int | None = None,
) -> list[dict]:
    rows = list(store.calendar_events.values())
    if event_type:
        rows = [e for e in rows if e["event_type"].lower() == event_type.lower()]
    if user_id is not None:
        saved_ids = {
            item["policy_id"]
            for item in store.saved_policies.values()
            if item["user_id"] == user_id
        }
        recommended_ids = {item["policyId"] for item in recommendations(user_id)}
        allowed = saved_ids | recommended_ids
        visible = []
        for event in rows:
            kind = (event.get("event_type") or "").upper()
            if kind == "POLICY" and event.get("policy_id") not in allowed:
                continue
            if kind == "USER" and event.get("user_id") != user_id:
                continue
            visible.append(event)
        rows = visible
    if year:
        rows = [e for e in rows if e["due_date"].year == year]
    if month:
        rows = [e for e in rows if e["due_date"].month == month]
    rows.sort(key=lambda e: e["due_date"])
    return [_to_item(e, user_id) for e in rows]


def create_personal_event(
    user_id: int,
    title: str,
    due_date: date,
    description: str = "",
    remind: bool = True,
    notify_at: datetime | None = None,
) -> dict:
    eid = store.next_id("event")
    store.calendar_events[eid] = {
        "id": eid,
        "event_type": "USER",
        "business_type": None,
        "policy_id": None,
        "user_id": user_id,
        "title": title.strip(),
        "due_date": due_date,
        "description": (description or "").strip(),
    }
    persist()
    if remind:
        when = notify_at or datetime.combine(due_date, datetime.min.time()).replace(hour=9)
        create_reminder(user_id, eid, when)
    return _to_item(store.calendar_events[eid], user_id)


def delete_personal_event(user_id: int, event_id: int) -> None:
    event = store.calendar_events.get(event_id)
    if not event or event.get("event_type") != "USER" or event.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="내 일정을 찾을 수 없습니다.")
    gone = [rid for rid, row in store.reminders.items() if row["event_id"] == event_id]
    for rid in gone:
        del store.reminders[rid]
    del store.calendar_events[event_id]
    persist()


def list_reminders(user_id: int) -> list[dict]:
    items = []
    for reminder in store.reminders.values():
        if reminder["user_id"] != user_id:
            continue
        event = store.calendar_events.get(reminder["event_id"])
        if not event:
            continue
        due = event["due_date"]
        notify_at = reminder["notify_at"]
        items.append(
            {
                "reminderId": reminder["id"],
                "eventId": reminder["event_id"],
                "title": event["title"],
                "dueDate": due,
                "notifyAt": notify_at,
                "dueSoon": 0 <= (due - date.today()).days <= 3,
                "arrived": notify_at <= datetime.now(),
            }
        )
    return items


def create_reminder(user_id: int, event_id: int, notify_at: datetime) -> int:
    if event_id not in store.calendar_events:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    for existing in store.reminders.values():
        if existing["user_id"] == user_id and existing["event_id"] == event_id:
            existing["notify_at"] = notify_at
            existing["dispatched"] = False
            persist()
            if notify_at <= datetime.now():
                from services.notify_service import dispatch_due_reminders

                dispatch_due_reminders()
            return existing["id"]
    rid = store.next_id("reminder")
    store.reminders[rid] = {
        "id": rid,
        "user_id": user_id,
        "event_id": event_id,
        "notify_at": notify_at,
        "created_at": datetime.now(),
        "dispatched": False,
    }
    persist()
    if notify_at <= datetime.now():
        from services.notify_service import dispatch_due_reminders

        dispatch_due_reminders()
    return rid


def delete_reminder(user_id: int, reminder_id: int) -> None:
    reminder = store.reminders.get(reminder_id)
    if not reminder or reminder["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="리마인더를 찾을 수 없습니다.")
    del store.reminders[reminder_id]
    persist()
