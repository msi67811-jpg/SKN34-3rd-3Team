"""Entity queries used by services. Row-level only — no TRUNCATE."""

from __future__ import annotations

from datetime import date, datetime

from core import db


def get_user(user_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))


def get_user_by_email(email: str) -> dict | None:
    return db.fetchone("SELECT * FROM users WHERE email = ?", (email,))


def create_user(email: str, password_hash: str, name: str) -> int:
    return db.insert(
        "INSERT INTO users(email,password_hash,name,age,region,phone,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (email, password_hash, name, None, None, "", "active", db._iso(datetime.now())),
    )


def update_user(user_id: int, fields: dict) -> None:
    mapping = {
        "name": "name",
        "age": "age",
        "region": "region",
        "phone": "phone",
        "status": "status",
    }
    sets = []
    params: list = []
    for src, column in mapping.items():
        if src in fields and fields[src] is not None:
            sets.append(f"{column} = ?")
            params.append(fields[src])
    if not sets:
        return
    params.append(user_id)
    db.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", tuple(params))


def list_users(offset: int = 0, limit: int = 20) -> list[dict]:
    return db.fetchall("SELECT * FROM users ORDER BY id LIMIT ? OFFSET ?", (limit, offset))


def get_admin(admin_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM admin_users WHERE id = ?", (admin_id,))


def get_admin_by_email(email: str) -> dict | None:
    return db.fetchone("SELECT * FROM admin_users WHERE email = ?", (email,))


def get_profile(user_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM business_profiles WHERE user_id = ?", (user_id,))


def upsert_profile(user_id: int, payload: dict) -> None:
    current = get_profile(user_id) or {
        "user_id": user_id,
        "business_type": None,
        "industry": None,
        "business_registered_at": None,
        "founded_at": None,
    }
    mapping = {
        "businessType": "business_type",
        "industry": "industry",
        "businessRegisteredAt": "business_registered_at",
        "foundedAt": "founded_at",
    }
    for src, dest in mapping.items():
        if payload.get(src) is not None:
            current[dest] = payload[src]
    if get_profile(user_id):
        db.execute(
            "UPDATE business_profiles SET business_type=?, industry=?, business_registered_at=?, founded_at=? WHERE user_id=?",
            (
                current.get("business_type"),
                current.get("industry"),
                db._iso(current.get("business_registered_at")),
                db._iso(current.get("founded_at")),
                user_id,
            ),
        )
        return
    db.insert(
        "INSERT INTO business_profiles(user_id,business_type,industry,business_registered_at,founded_at) VALUES (?,?,?,?,?)",
        (
            user_id,
            current.get("business_type"),
            current.get("industry"),
            db._iso(current.get("business_registered_at")),
            db._iso(current.get("founded_at")),
        ),
    )


def get_tax_info(user_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM tax_info WHERE user_id = ?", (user_id,))


def upsert_tax_info(user_id: int, tax_type: str, details: str) -> None:
    now = db._iso(datetime.now())
    if get_tax_info(user_id):
        db.execute(
            "UPDATE tax_info SET tax_type=?, details=?, updated_at=? WHERE user_id=?",
            (tax_type, details, now, user_id),
        )
        return
    db.insert(
        "INSERT INTO tax_info(user_id,tax_type,details,updated_at) VALUES (?,?,?,?)",
        (user_id, tax_type, details, now),
    )


def insert_tax_reduction(user_id: int, eligible: bool, reasons: list, legal_basis: str) -> None:
    db.insert(
        "INSERT INTO tax_reduction_results(user_id,eligible,reasons,legal_basis,judged_at) VALUES (?,?,?,?,?)",
        (user_id, db.flag(eligible), db.dumps(reasons), legal_basis, db._iso(datetime.now())),
    )


def latest_tax_reduction(user_id: int) -> dict | None:
    return db.fetchone(
        "SELECT * FROM tax_reduction_results WHERE user_id = ? ORDER BY judged_at DESC, id DESC LIMIT 1",
        (user_id,),
    )


def insert_chat(user_id: int, category: str, question: str, answer: str, sources: list[dict]) -> int:
    mid = db.insert(
        "INSERT INTO chat_messages(user_id,category,question,answer,created_at) VALUES (?,?,?,?,?)",
        (user_id, category, question, answer, db._iso(datetime.now())),
    )
    for item in sources:
        db.insert(
            "INSERT INTO answer_sources(message_id,title,url,excerpt) VALUES (?,?,?,?)",
            (mid, item.get("title"), item.get("url"), item.get("excerpt")),
        )
    return mid


def get_chat(message_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM chat_messages WHERE id = ?", (message_id,))


def chat_sources(message_id: int) -> list[dict]:
    return db.fetchall("SELECT title, url, excerpt FROM answer_sources WHERE message_id = ?", (message_id,))


def list_chats(user_id: int, category: str | None = None) -> list[dict]:
    if category:
        return db.fetchall(
            "SELECT * FROM chat_messages WHERE user_id = ? AND category = ? ORDER BY created_at",
            (user_id, category),
        )
    return db.fetchall(
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    )


def delete_chats(user_id: int, category: str | None = None) -> int:
    rows = list_chats(user_id, category)
    for row in rows:
        db.execute("DELETE FROM answer_sources WHERE message_id = ?", (row["id"],))
        db.execute("DELETE FROM chat_messages WHERE id = ?", (row["id"],))
    return len(rows)


def list_events() -> list[dict]:
    return db.fetchall("SELECT * FROM calendar_events")


def get_event(event_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM calendar_events WHERE id = ?", (event_id,))


def insert_event(
    event_type: str,
    title: str,
    due_date: date | str,
    description: str = "",
    *,
    business_type: str | None = None,
    policy_id: int | None = None,
    user_id: int | None = None,
) -> int:
    return db.insert(
        "INSERT INTO calendar_events(event_type,business_type,policy_id,user_id,title,due_date,description) VALUES (?,?,?,?,?,?,?)",
        (event_type, business_type, policy_id, user_id, title, db._iso(due_date), description),
    )


def delete_event(event_id: int) -> None:
    db.execute("DELETE FROM reminders WHERE event_id = ?", (event_id,))
    db.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))


def list_reminders(user_id: int) -> list[dict]:
    return db.fetchall("SELECT * FROM reminders WHERE user_id = ?", (user_id,))


def get_reminder(reminder_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM reminders WHERE id = ?", (reminder_id,))


def get_reminder_for_event(user_id: int, event_id: int) -> dict | None:
    return db.fetchone(
        "SELECT * FROM reminders WHERE user_id = ? AND event_id = ?",
        (user_id, event_id),
    )


def upsert_reminder(user_id: int, event_id: int, notify_at: datetime) -> int:
    existing = get_reminder_for_event(user_id, event_id)
    if existing:
        db.execute(
            "UPDATE reminders SET notify_at=?, dispatched=? WHERE id=?",
            (db._iso(notify_at), db.flag(False), existing["id"]),
        )
        return existing["id"]
    return db.insert(
        "INSERT INTO reminders(user_id,event_id,notify_at,created_at,dispatched) VALUES (?,?,?,?,?)",
        (user_id, event_id, db._iso(notify_at), db._iso(datetime.now()), db.flag(False)),
    )


def delete_reminder(reminder_id: int) -> None:
    db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))


def due_reminders() -> list[dict]:
    return db.fetchall("SELECT * FROM reminders WHERE dispatched = ?", (db.flag(False),))


def mark_reminder_dispatched(reminder_id: int) -> None:
    db.execute("UPDATE reminders SET dispatched = ? WHERE id = ?", (db.flag(True), reminder_id))


def saved_policy_ids(user_id: int) -> set[int]:
    rows = db.fetchall("SELECT policy_id FROM saved_policies WHERE user_id = ?", (user_id,))
    return {row["policy_id"] for row in rows}


def list_notifications(user_id: int) -> list[dict]:
    return db.fetchall(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )


def unread_count(user_id: int) -> int:
    return int(
        db.scalar(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read_flag = ?",
            (user_id, db.flag(False)),
        )
        or 0
    )


def mark_notifications_read(user_id: int, notification_id: int | None = None) -> None:
    if notification_id is None:
        db.execute(
            "UPDATE notifications SET read_flag = ? WHERE user_id = ?",
            (db.flag(True), user_id),
        )
        return
    db.execute(
        "UPDATE notifications SET read_flag = ? WHERE user_id = ? AND id = ?",
        (db.flag(True), user_id, notification_id),
    )


def insert_notification(user_id: int, kind: str, title: str, body: str, channel: str, status: str = "delivered") -> int:
    return db.insert(
        "INSERT INTO notifications(user_id,kind,title,body,channel,status,read_flag,created_at) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, kind, title, body, channel, status, db.flag(False), db._iso(datetime.now())),
    )


def insert_receipt(user_id: int, filename: str) -> int:
    return db.insert(
        "INSERT INTO receipts(user_id,image_url,status,created_at) VALUES (?,?,?,?)",
        (user_id, filename, "done", db._iso(datetime.now())),
    )


def insert_extraction(receipt_id: int, spent, vendor: str, amount: int, items: list) -> int:
    return db.insert(
        "INSERT INTO receipt_extractions(receipt_id,date,vendor,amount,items) VALUES (?,?,?,?,?)",
        (receipt_id, db._iso(spent), vendor, amount, db.dumps(items)),
    )


def insert_expense(receipt_id: int, user_id: int, category: str, amount: int, spent, deductible: bool, confidence: float, basis: str) -> int:
    return db.insert(
        "INSERT INTO expenses(receipt_id,user_id,category,amount,date,deductible,deductible_confidence,deductible_basis) VALUES (?,?,?,?,?,?,?,?)",
        (receipt_id, user_id, category, amount, db._iso(spent), db.flag(deductible), confidence, basis),
    )


def get_receipt(receipt_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM receipts WHERE id = ?", (receipt_id,))


def get_extraction(receipt_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM receipt_extractions WHERE receipt_id = ?", (receipt_id,))


def get_expense(expense_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM expenses WHERE id = ?", (expense_id,))


def list_expenses(user_id: int) -> list[dict]:
    return db.fetchall("SELECT * FROM expenses WHERE user_id = ?", (user_id,))


def update_expense(expense_id: int, category: str, deductible: bool, confidence: float, basis: str) -> None:
    db.execute(
        "UPDATE expenses SET category=?, deductible=?, deductible_confidence=?, deductible_basis=? WHERE id=?",
        (category, db.flag(deductible), confidence, basis, expense_id),
    )


def delete_expense(expense_id: int, receipt_id: int) -> None:
    db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    leftover = db.scalar("SELECT COUNT(*) FROM expenses WHERE receipt_id = ?", (receipt_id,))
    if int(leftover or 0) == 0:
        db.execute("DELETE FROM receipt_extractions WHERE receipt_id = ?", (receipt_id,))
        db.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))


def list_policies() -> list[dict]:
    return db.fetchall("SELECT * FROM policies")


def get_policy(policy_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM policies WHERE id = ?", (policy_id,))


def announcement_of(policy_id: int) -> dict | None:
    return db.fetchone(
        "SELECT * FROM announcements WHERE policy_id = ? ORDER BY id DESC LIMIT 1",
        (policy_id,),
    )


def announcement_map() -> dict[int, dict]:
    mapped: dict[int, dict] = {}
    for row in db.fetchall("SELECT * FROM announcements ORDER BY id"):
        pid = row.get("policy_id")
        if pid is not None:
            mapped[pid] = row
    return mapped


def get_announcement(announcement_id: int) -> dict | None:
    return db.fetchone("SELECT * FROM announcements WHERE id = ?", (announcement_id,))


def get_summary(announcement_id: int) -> dict | None:
    return db.fetchone(
        "SELECT * FROM announcement_summaries WHERE announcement_id = ?",
        (announcement_id,),
    )


def upsert_summary(announcement_id: int, summary: dict) -> None:
    if get_summary(announcement_id):
        db.execute(
            "UPDATE announcement_summaries SET target=?, benefit=?, period=?, documents=?, notes=?, source=?, llm_used=? WHERE announcement_id=?",
            (
                summary.get("target"),
                summary.get("benefit"),
                summary.get("period"),
                summary.get("documents"),
                summary.get("notes"),
                summary.get("source"),
                db.flag(bool(summary.get("llm_used"))),
                announcement_id,
            ),
        )
        return
    db.insert(
        "INSERT INTO announcement_summaries(announcement_id,target,benefit,period,documents,notes,source,llm_used) VALUES (?,?,?,?,?,?,?,?)",
        (
            announcement_id,
            summary.get("target"),
            summary.get("benefit"),
            summary.get("period"),
            summary.get("documents"),
            summary.get("notes"),
            summary.get("source"),
            db.flag(bool(summary.get("llm_used"))),
        ),
    )


def save_policy(user_id: int, policy_id: int) -> None:
    existing = db.fetchone(
        "SELECT id FROM saved_policies WHERE user_id = ? AND policy_id = ?",
        (user_id, policy_id),
    )
    if existing:
        return
    db.insert(
        "INSERT INTO saved_policies(user_id,policy_id,saved_at) VALUES (?,?,?)",
        (user_id, policy_id, db._iso(datetime.now())),
    )


def insert_policy(admin_id: int, body: dict) -> int:
    return db.insert(
        "INSERT INTO policies(admin_id,title,region,industry,target,benefit,eligibility_rule,source,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            admin_id,
            body.get("title") or "제목 없음",
            body.get("region") or "전국",
            body.get("industry") or "전 업종",
            body.get("target") or "",
            body.get("benefit") or body.get("content") or "",
            body.get("eligibilityRule") or "",
            body.get("source") or "",
            db._iso(datetime.now()),
        ),
    )


def insert_announcement(policy_id: int | None, body: dict, start, end) -> int:
    return db.insert(
        "INSERT INTO announcements(policy_id,raw_content,source_url,apply_start_date,apply_end_date,apply_method,created_at) VALUES (?,?,?,?,?,?,?)",
        (
            policy_id,
            body.get("content") or body.get("benefit") or body.get("title") or "",
            body.get("sourceUrl") or body.get("source") or "",
            db._iso(start),
            db._iso(end),
            body.get("applyMethod") or "",
            db._iso(datetime.now()),
        ),
    )


def list_announcements() -> list[dict]:
    return db.fetchall("SELECT * FROM announcements")


def list_tax_documents() -> list[dict]:
    return db.fetchall("SELECT * FROM tax_documents")


def insert_tax_document(admin_id: int, body: dict) -> int:
    return db.insert(
        "INSERT INTO tax_documents(admin_id,title,law_name,content,source,created_at) VALUES (?,?,?,?,?,?)",
        (
            admin_id,
            body.get("title"),
            body.get("lawName"),
            body.get("content"),
            body.get("source"),
            db._iso(datetime.now()),
        ),
    )


def count(table: str) -> int:
    return int(db.scalar(f"SELECT COUNT(*) FROM {table}") or 0)


def count_users_by_status(status: str) -> int:
    return int(db.scalar("SELECT COUNT(*) FROM users WHERE COALESCE(status,'active') = ?", (status,)) or 0)
