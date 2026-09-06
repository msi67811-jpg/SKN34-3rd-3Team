"""SQLite persistence for the in-memory store. Schema follows DB/schema.sql (no pgvector)."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from core.config import DATA_DIR, SQLITE_PATH
from core import store

DDL = """
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    age INTEGER,
    region TEXT,
    phone TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS business_profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,
    business_type TEXT,
    industry TEXT,
    business_registered_at TEXT,
    founded_at TEXT
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    category TEXT,
    question TEXT,
    answer TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS answer_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,
    title TEXT,
    url TEXT,
    excerpt TEXT
);
CREATE TABLE IF NOT EXISTS tax_info (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    tax_type TEXT,
    details TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS policies (
    id INTEGER PRIMARY KEY,
    admin_id INTEGER,
    title TEXT NOT NULL,
    region TEXT,
    industry TEXT,
    target TEXT,
    benefit TEXT,
    eligibility_rule TEXT,
    source TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    business_type TEXT,
    policy_id INTEGER,
    user_id INTEGER,
    title TEXT,
    due_date TEXT,
    description TEXT
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    event_id INTEGER,
    notify_at TEXT,
    created_at TEXT,
    dispatched INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tax_reduction_results (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    eligible INTEGER,
    reasons TEXT,
    legal_basis TEXT,
    judged_at TEXT
);
CREATE TABLE IF NOT EXISTS receipts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    image_url TEXT,
    status TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS receipt_extractions (
    id INTEGER PRIMARY KEY,
    receipt_id INTEGER UNIQUE,
    date TEXT,
    vendor TEXT,
    amount INTEGER,
    items TEXT
);
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY,
    receipt_id INTEGER,
    user_id INTEGER,
    category TEXT,
    amount INTEGER,
    date TEXT,
    deductible INTEGER,
    deductible_confidence REAL,
    deductible_basis TEXT
);
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY,
    policy_id INTEGER,
    raw_content TEXT,
    source_url TEXT,
    apply_start_date TEXT,
    apply_end_date TEXT,
    apply_method TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS announcement_summaries (
    id INTEGER PRIMARY KEY,
    announcement_id INTEGER UNIQUE,
    target TEXT,
    benefit TEXT,
    period TEXT,
    documents TEXT,
    notes TEXT,
    source TEXT,
    llm_used INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS saved_policies (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    policy_id INTEGER,
    saved_at TEXT,
    UNIQUE (user_id, policy_id)
);
CREATE TABLE IF NOT EXISTS tax_documents (
    id INTEGER PRIMARY KEY,
    admin_id INTEGER,
    title TEXT,
    law_name TEXT,
    content TEXT,
    source TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS meta_ids (
    name TEXT PRIMARY KEY,
    value INTEGER
);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    kind TEXT,
    title TEXT,
    body TEXT,
    channel TEXT,
    status TEXT,
    read_flag INTEGER DEFAULT 0,
    created_at TEXT
);
"""


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def init_db() -> str:
    """Create tables. Prefer Postgres, then SQLite."""
    conn = _connect()
    try:
        conn.executescript(DDL)
        _migrate(conn)
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count:
            _load(conn)
            sqlite_mode = "sqlite-loaded"
        else:
            _save(conn)
            sqlite_mode = "sqlite-seeded"
    finally:
        conn.close()

    from core.postgres import init_postgres

    postgres_mode = init_postgres()
    return postgres_mode or sqlite_mode


def persist() -> None:
    conn = _connect()
    try:
        conn.executescript(DDL)
        _migrate(conn)
        _save(conn)
    finally:
        conn.close()
    from core.postgres import persist_postgres

    persist_postgres()


def _migrate(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "status" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    reminder_columns = {row[1] for row in conn.execute("PRAGMA table_info(reminders)")}
    if "dispatched" not in reminder_columns:
        conn.execute("ALTER TABLE reminders ADD COLUMN dispatched INTEGER DEFAULT 0")
    calendar_columns = {row[1] for row in conn.execute("PRAGMA table_info(calendar_events)")}
    if "user_id" not in calendar_columns:
        conn.execute("ALTER TABLE calendar_events ADD COLUMN user_id INTEGER")
    if "phone" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")


def db_path() -> str:
    return str(Path(SQLITE_PATH).resolve())


def _clear(conn: sqlite3.Connection) -> None:
    tables = [
        "answer_sources",
        "saved_policies",
        "announcement_summaries",
        "announcements",
        "expenses",
        "receipt_extractions",
        "receipts",
        "tax_reduction_results",
        "reminders",
        "calendar_events",
        "tax_documents",
        "policies",
        "tax_info",
        "chat_messages",
        "business_profiles",
        "users",
        "admin_users",
        "notifications",
        "meta_ids",
    ]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")


def _save(conn: sqlite3.Connection) -> None:
    _clear(conn)
    for row in store.admins.values():
        conn.execute(
            "INSERT INTO admin_users(id,email,password_hash,role,created_at) VALUES (?,?,?,?,?)",
            (row["id"], row["email"], row["password_hash"], row.get("role"), _iso(row.get("created_at"))),
        )
    for row in store.users.values():
        conn.execute(
            "INSERT INTO users(id,email,password_hash,name,age,region,phone,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row["email"],
                row["password_hash"],
                row.get("name"),
                row.get("age"),
                row.get("region"),
                row.get("phone") or "",
                row.get("status") or "active",
                _iso(row.get("created_at")),
            ),
        )
    for row in store.business_profiles.values():
        conn.execute(
            "INSERT INTO business_profiles(id,user_id,business_type,industry,business_registered_at,founded_at) VALUES (?,?,?,?,?,?)",
            (
                row["id"],
                row["user_id"],
                row.get("business_type"),
                row.get("industry"),
                _iso(row.get("business_registered_at")),
                _iso(row.get("founded_at")),
            ),
        )
    for row in store.chat_messages.values():
        conn.execute(
            "INSERT INTO chat_messages(id,user_id,category,question,answer,created_at) VALUES (?,?,?,?,?,?)",
            (
                row["id"],
                row["user_id"],
                row.get("category"),
                row.get("question"),
                row.get("answer"),
                _iso(row.get("created_at")),
            ),
        )
    for message_id, sources in store.answer_sources.items():
        for src in sources:
            conn.execute(
                "INSERT INTO answer_sources(message_id,title,url,excerpt) VALUES (?,?,?,?)",
                (message_id, src.get("title"), src.get("url"), src.get("excerpt")),
            )
    for row in store.tax_infos.values():
        conn.execute(
            "INSERT INTO tax_info(id,user_id,tax_type,details,updated_at) VALUES (?,?,?,?,?)",
            (row["id"], row["user_id"], row.get("tax_type"), row.get("details"), _iso(row.get("updated_at"))),
        )
    for row in store.policies.values():
        conn.execute(
            "INSERT INTO policies(id,admin_id,title,region,industry,target,benefit,eligibility_rule,source,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row.get("admin_id"),
                row["title"],
                row.get("region"),
                row.get("industry"),
                row.get("target"),
                row.get("benefit"),
                row.get("eligibility_rule"),
                row.get("source"),
                _iso(row.get("created_at")),
            ),
        )
    for row in store.calendar_events.values():
        conn.execute(
            "INSERT INTO calendar_events(id,event_type,business_type,policy_id,user_id,title,due_date,description) VALUES (?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row["event_type"],
                row.get("business_type"),
                row.get("policy_id"),
                row.get("user_id"),
                row.get("title"),
                _iso(row.get("due_date")),
                row.get("description"),
            ),
        )
    for row in store.reminders.values():
        conn.execute(
            "INSERT INTO reminders(id,user_id,event_id,notify_at,created_at,dispatched) VALUES (?,?,?,?,?,?)",
            (
                row["id"],
                row["user_id"],
                row["event_id"],
                _iso(row.get("notify_at")),
                _iso(row.get("created_at")),
                1 if row.get("dispatched") else 0,
            ),
        )
    for user_id, row in store.tax_reduction_results.items():
        conn.execute(
            "INSERT INTO tax_reduction_results(id,user_id,eligible,reasons,legal_basis,judged_at) VALUES (?,?,?,?,?,?)",
            (
                row.get("id") or user_id,
                user_id,
                1 if row.get("eligible") else 0,
                json.dumps(row.get("reasons") or [], ensure_ascii=False),
                row.get("legalBasis") or row.get("legal_basis"),
                _iso(row.get("judged_at")),
            ),
        )
    for row in store.receipts.values():
        conn.execute(
            "INSERT INTO receipts(id,user_id,image_url,status,created_at) VALUES (?,?,?,?,?)",
            (row["id"], row["user_id"], row.get("image_url"), row.get("status"), _iso(row.get("created_at"))),
        )
    for receipt_id, row in store.receipt_extractions.items():
        items = row.get("items") or []
        conn.execute(
            "INSERT INTO receipt_extractions(id,receipt_id,date,vendor,amount,items) VALUES (?,?,?,?,?,?)",
            (
                row.get("id") or receipt_id,
                receipt_id,
                _iso(row.get("date")),
                row.get("vendor"),
                row.get("amount"),
                json.dumps(items, ensure_ascii=False),
            ),
        )
    for row in store.expenses.values():
        conn.execute(
            "INSERT INTO expenses(id,receipt_id,user_id,category,amount,date,deductible,deductible_confidence,deductible_basis) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row.get("receipt_id"),
                row.get("user_id"),
                row.get("category"),
                row.get("amount"),
                _iso(row.get("date")),
                1 if row.get("deductible") else 0,
                row.get("deductible_confidence"),
                row.get("deductible_basis"),
            ),
        )
    for row in store.announcements.values():
        conn.execute(
            "INSERT INTO announcements(id,policy_id,raw_content,source_url,apply_start_date,apply_end_date,apply_method,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row["policy_id"],
                row.get("raw_content"),
                row.get("source_url"),
                _iso(row.get("apply_start_date")),
                _iso(row.get("apply_end_date")),
                row.get("apply_method"),
                _iso(row.get("created_at")),
            ),
        )
    for announcement_id, row in store.announcement_summaries.items():
        conn.execute(
            "INSERT INTO announcement_summaries(id,announcement_id,target,benefit,period,documents,notes,source,llm_used) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                row.get("id") or announcement_id,
                announcement_id,
                row.get("target"),
                row.get("benefit"),
                row.get("period"),
                row.get("documents"),
                row.get("notes"),
                row.get("source"),
                1 if row.get("llm_used") else 0,
            ),
        )
    for row in store.saved_policies.values():
        conn.execute(
            "INSERT OR IGNORE INTO saved_policies(id,user_id,policy_id,saved_at) VALUES (?,?,?,?)",
            (row["id"], row["user_id"], row["policy_id"], _iso(row.get("saved_at"))),
        )
    for row in store.tax_documents.values():
        conn.execute(
            "INSERT INTO tax_documents(id,admin_id,title,law_name,content,source,created_at) VALUES (?,?,?,?,?,?,?)",
            (
                row["id"],
                row.get("admin_id"),
                row.get("title"),
                row.get("law_name"),
                row.get("content"),
                row.get("source"),
                _iso(row.get("created_at")),
            ),
        )
    for row in store.notifications.values():
        conn.execute(
            "INSERT INTO notifications(id,user_id,kind,title,body,channel,status,read_flag,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row["user_id"],
                row.get("kind"),
                row.get("title"),
                row.get("body"),
                row.get("channel"),
                row.get("status"),
                1 if row.get("read") else 0,
                _iso(row.get("created_at")),
            ),
        )
    for name, value in store._next_ids.items():
        conn.execute("INSERT INTO meta_ids(name,value) VALUES (?,?)", (name, value))
    conn.commit()


def _load(conn: sqlite3.Connection) -> None:
    store.users.clear()
    store.users_by_email.clear()
    store.admins.clear()
    store.admins_by_email.clear()
    store.business_profiles.clear()
    store.tax_infos.clear()
    store.chat_messages.clear()
    store.answer_sources.clear()
    store.reminders.clear()
    store.tax_reduction_results.clear()
    store.receipts.clear()
    store.receipt_extractions.clear()
    store.expenses.clear()
    store.saved_policies.clear()
    store.tax_documents.clear()
    store.policies.clear()
    store.announcements.clear()
    store.announcement_summaries.clear()
    store.calendar_events.clear()
    store.notifications.clear()
    store._next_ids.clear()

    for row in conn.execute("SELECT * FROM admin_users"):
        item = dict(row)
        item["created_at"] = _parse_dt(item.get("created_at"))
        store.admins[item["id"]] = item
        store.admins_by_email[item["email"]] = item["id"]
    for row in conn.execute("SELECT * FROM users"):
        item = dict(row)
        item["created_at"] = _parse_dt(item.get("created_at"))
        item["status"] = item.get("status") or "active"
        store.users[item["id"]] = item
        store.users_by_email[item["email"]] = item["id"]
    for row in conn.execute("SELECT * FROM business_profiles"):
        item = dict(row)
        item["business_registered_at"] = _parse_date(item.get("business_registered_at"))
        item["founded_at"] = _parse_date(item.get("founded_at"))
        store.business_profiles[item["user_id"]] = item
    for row in conn.execute("SELECT * FROM chat_messages"):
        item = dict(row)
        item["created_at"] = _parse_dt(item.get("created_at"))
        store.chat_messages[item["id"]] = item
    for row in conn.execute("SELECT * FROM answer_sources"):
        item = dict(row)
        store.answer_sources.setdefault(item["message_id"], []).append(
            {"title": item["title"], "url": item["url"], "excerpt": item["excerpt"]}
        )
    for row in conn.execute("SELECT * FROM tax_info"):
        item = dict(row)
        item["updated_at"] = _parse_dt(item.get("updated_at"))
        store.tax_infos[item["user_id"]] = item
    for row in conn.execute("SELECT * FROM policies"):
        item = dict(row)
        item["created_at"] = _parse_dt(item.get("created_at"))
        store.policies[item["id"]] = item
    for row in conn.execute("SELECT * FROM calendar_events"):
        item = dict(row)
        item["due_date"] = _parse_date(item.get("due_date"))
        store.calendar_events[item["id"]] = item
    for row in conn.execute("SELECT * FROM reminders"):
        item = dict(row)
        item["notify_at"] = _parse_dt(item.get("notify_at"))
        item["created_at"] = _parse_dt(item.get("created_at"))
        item["dispatched"] = bool(item.get("dispatched"))
        store.reminders[item["id"]] = item
    for row in conn.execute("SELECT * FROM tax_reduction_results"):
        item = dict(row)
        store.tax_reduction_results[item["user_id"]] = {
            "id": item["id"],
            "eligible": bool(item["eligible"]),
            "reasons": json.loads(item["reasons"] or "[]"),
            "legalBasis": item["legal_basis"],
            "judged_at": _parse_dt(item.get("judged_at")),
        }
    for row in conn.execute("SELECT * FROM receipts"):
        item = dict(row)
        item["created_at"] = _parse_dt(item.get("created_at"))
        store.receipts[item["id"]] = item
    for row in conn.execute("SELECT * FROM receipt_extractions"):
        item = dict(row)
        store.receipt_extractions[item["receipt_id"]] = {
            "id": item["id"],
            "receipt_id": item["receipt_id"],
            "date": _parse_date(item.get("date")),
            "vendor": item["vendor"],
            "amount": item["amount"],
            "items": json.loads(item["items"] or "[]"),
        }
    for row in conn.execute("SELECT * FROM expenses"):
        item = dict(row)
        store.expenses[item["id"]] = {
            "id": item["id"],
            "receipt_id": item["receipt_id"],
            "user_id": item["user_id"],
            "category": item["category"],
            "amount": item["amount"],
            "date": _parse_date(item.get("date")),
            "deductible": bool(item["deductible"]),
            "deductible_confidence": item["deductible_confidence"],
            "deductible_basis": item["deductible_basis"],
        }
    for row in conn.execute("SELECT * FROM announcements"):
        item = dict(row)
        item["apply_start_date"] = _parse_date(item.get("apply_start_date"))
        item["apply_end_date"] = _parse_date(item.get("apply_end_date"))
        item["created_at"] = _parse_dt(item.get("created_at"))
        store.announcements[item["id"]] = item
    for row in conn.execute("SELECT * FROM announcement_summaries"):
        item = dict(row)
        store.announcement_summaries[item["announcement_id"]] = {
            "id": item["id"],
            "announcement_id": item["announcement_id"],
            "target": item["target"],
            "benefit": item["benefit"],
            "period": item["period"],
            "documents": item["documents"],
            "notes": item["notes"],
            "source": item["source"],
            "llm_used": bool(item["llm_used"]),
        }
    for row in conn.execute("SELECT * FROM saved_policies"):
        item = dict(row)
        item["saved_at"] = _parse_dt(item.get("saved_at"))
        store.saved_policies[item["id"]] = item
    for row in conn.execute("SELECT * FROM tax_documents"):
        item = dict(row)
        item["created_at"] = _parse_dt(item.get("created_at"))
        store.tax_documents[item["id"]] = item
    try:
        notification_rows = conn.execute("SELECT * FROM notifications")
    except Exception:
        notification_rows = []
    for row in notification_rows:
        item = dict(row)
        item["created_at"] = _parse_dt(item.get("created_at"))
        item["read"] = bool(item.get("read_flag"))
        store.notifications[item["id"]] = item
    for row in conn.execute("SELECT * FROM meta_ids"):
        store._next_ids[row["name"]] = row["value"]
