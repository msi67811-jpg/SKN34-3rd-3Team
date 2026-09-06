"""Postgres + pgvector: schema extras, persist, and health."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from core.config import DATABASE_URL
from core import store

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SQL = PROJECT_ROOT / "DB" / "schema.sql"
EXTRAS_SQL = PROJECT_ROOT / "DB" / "app_extras.sql"


def _connect():
    try:
        import psycopg
    except ImportError:
        return None
    parsed = urlparse(DATABASE_URL)
    try:
        return psycopg.connect(
            host=parsed.hostname or "127.0.0.1",
            port=parsed.port or 5432,
            user=parsed.username or "admin",
            password=parsed.password or "admin1234",
            dbname=(parsed.path or "/startup_platform").lstrip("/") or "startup_platform",
            connect_timeout=3,
            autocommit=True,
        )
    except Exception:
        return None


def postgres_status() -> dict:
    conn = _connect()
    if conn is None:
        return {"reachable": False, "pgvector": False, "url": DATABASE_URL}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            has_vector = cur.fetchone() is not None
            cur.execute("SELECT to_regclass('public.users')")
            has_users = cur.fetchone()[0] is not None
            chunk_count = 0
            user_count = 0
            if has_users:
                cur.execute("SELECT COUNT(*) FROM users")
                user_count = int(cur.fetchone()[0])
            if has_vector:
                cur.execute("SELECT to_regclass('public.rag_chunks')")
                if cur.fetchone()[0]:
                    cur.execute("SELECT COUNT(*) FROM rag_chunks")
                    chunk_count = int(cur.fetchone()[0])
        return {
            "reachable": True,
            "pgvector": bool(has_vector),
            "url": DATABASE_URL,
            "ragChunks": chunk_count,
            "users": user_count,
        }
    except Exception:
        return {"reachable": False, "pgvector": False, "url": DATABASE_URL}
    finally:
        conn.close()


def init_postgres() -> str | None:
    conn = _connect()
    if conn is None:
        return None
    try:
        _ensure_schema(conn)
        _ensure_extras(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.users')")
            if cur.fetchone()[0] is None:
                return None
            cur.execute("SELECT COUNT(*) FROM users")
            count = int(cur.fetchone()[0])
        if count:
            load_postgres(conn)
            return "postgres-loaded"
        save_postgres(conn)
        return "postgres-seeded"
    except Exception:
        return None
    finally:
        conn.close()


def persist_postgres() -> bool:
    conn = _connect()
    if conn is None:
        return False
    try:
        _ensure_extras(conn)
        save_postgres(conn)
        return True
    except Exception:
        return False
    finally:
        conn.close()


def _run_sql_file(conn, path: Path) -> None:
    if not path.is_file():
        return
    for statement in path.read_text(encoding="utf-8").split(";"):
        sql = "\n".join(
            line for line in statement.splitlines() if not line.strip().startswith("--")
        ).strip()
        if sql:
            conn.execute(sql)


def _ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.users')")
        if cur.fetchone()[0] is not None:
            return
    _run_sql_file(conn, SCHEMA_SQL)


def _ensure_extras(conn) -> None:
    _run_sql_file(conn, EXTRAS_SQL)


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _as_date(value):
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def save_postgres(conn) -> None:
    tables = [
        "notifications",
        "saved_policies",
        "announcement_summaries",
        "answer_sources",
        "expenses",
        "receipt_extractions",
        "receipts",
        "tax_reduction_results",
        "reminders",
        "calendar_events",
        "announcements",
        "tax_documents",
        "policies",
        "tax_info",
        "chat_messages",
        "business_profiles",
        "users",
        "admin_users",
        "meta_ids",
    ]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE " + ", ".join(tables) + " RESTART IDENTITY CASCADE")
        for row in store.admins.values():
            cur.execute(
                "INSERT INTO admin_users(id,email,password_hash,role,created_at) VALUES (%s,%s,%s,%s,%s)",
                (row["id"], row["email"], row["password_hash"], row.get("role"), row.get("created_at")),
            )
        for row in store.users.values():
            cur.execute(
                "INSERT INTO users(id,email,password_hash,name,age,region,phone,status,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row["email"],
                    row["password_hash"],
                    row.get("name"),
                    row.get("age"),
                    row.get("region"),
                    row.get("phone") or "",
                    row.get("status") or "active",
                    row.get("created_at"),
                ),
            )
        for row in store.business_profiles.values():
            cur.execute(
                "INSERT INTO business_profiles(id,user_id,business_type,industry,business_registered_at,founded_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row["user_id"],
                    row.get("business_type"),
                    row.get("industry"),
                    row.get("business_registered_at"),
                    row.get("founded_at"),
                ),
            )
        for row in store.chat_messages.values():
            cur.execute(
                "INSERT INTO chat_messages(id,user_id,category,question,answer,created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row["user_id"],
                    row.get("category"),
                    row.get("question"),
                    row.get("answer"),
                    row.get("created_at"),
                ),
            )
        for message_id, sources in store.answer_sources.items():
            for src in sources:
                cur.execute(
                    "INSERT INTO answer_sources(message_id,title,url,excerpt) VALUES (%s,%s,%s,%s)",
                    (message_id, src.get("title"), src.get("url"), src.get("excerpt")),
                )
        for row in store.tax_infos.values():
            cur.execute(
                "INSERT INTO tax_info(id,user_id,tax_type,details,updated_at) VALUES (%s,%s,%s,%s,%s)",
                (row["id"], row["user_id"], row.get("tax_type"), row.get("details"), row.get("updated_at")),
            )
        for row in store.policies.values():
            cur.execute(
                "INSERT INTO policies(id,admin_id,title,region,industry,target,benefit,eligibility_rule,source,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
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
                    row.get("created_at"),
                ),
            )
        for row in store.calendar_events.values():
            cur.execute(
                "INSERT INTO calendar_events(id,event_type,business_type,policy_id,user_id,title,due_date,description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row["event_type"],
                    row.get("business_type"),
                    row.get("policy_id"),
                    row.get("user_id"),
                    row.get("title"),
                    row.get("due_date"),
                    row.get("description"),
                ),
            )
        for row in store.reminders.values():
            cur.execute(
                "INSERT INTO reminders(id,user_id,event_id,notify_at,created_at,dispatched) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row["user_id"],
                    row["event_id"],
                    row.get("notify_at"),
                    row.get("created_at"),
                    bool(row.get("dispatched")),
                ),
            )
        for user_id, row in store.tax_reduction_results.items():
            cur.execute(
                "INSERT INTO tax_reduction_results(id,user_id,eligible,reasons,legal_basis,judged_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    row.get("id") or user_id,
                    user_id,
                    bool(row.get("eligible")),
                    json.dumps(row.get("reasons") or [], ensure_ascii=False),
                    row.get("legalBasis") or row.get("legal_basis"),
                    row.get("judged_at"),
                ),
            )
        for row in store.receipts.values():
            cur.execute(
                "INSERT INTO receipts(id,user_id,image_url,status,created_at) VALUES (%s,%s,%s,%s,%s)",
                (row["id"], row["user_id"], row.get("image_url"), row.get("status"), row.get("created_at")),
            )
        for receipt_id, row in store.receipt_extractions.items():
            cur.execute(
                "INSERT INTO receipt_extractions(id,receipt_id,date,vendor,amount,items) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    row.get("id") or receipt_id,
                    receipt_id,
                    row.get("date"),
                    row.get("vendor"),
                    row.get("amount"),
                    json.dumps(row.get("items") or [], ensure_ascii=False),
                ),
            )
        for row in store.expenses.values():
            cur.execute(
                "INSERT INTO expenses(id,receipt_id,user_id,category,amount,date,deductible,deductible_confidence,deductible_basis) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row.get("receipt_id"),
                    row.get("user_id"),
                    row.get("category"),
                    row.get("amount"),
                    row.get("date"),
                    bool(row.get("deductible")),
                    row.get("deductible_confidence"),
                    row.get("deductible_basis"),
                ),
            )
        for row in store.announcements.values():
            cur.execute(
                "INSERT INTO announcements(id,policy_id,raw_content,source_url,apply_start_date,apply_end_date,apply_method,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row["policy_id"],
                    row.get("raw_content"),
                    row.get("source_url"),
                    row.get("apply_start_date"),
                    row.get("apply_end_date"),
                    row.get("apply_method"),
                    row.get("created_at"),
                ),
            )
        for announcement_id, row in store.announcement_summaries.items():
            cur.execute(
                "INSERT INTO announcement_summaries(id,announcement_id,target,benefit,period,documents,notes,source,llm_used) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row.get("id") or announcement_id,
                    announcement_id,
                    row.get("target"),
                    row.get("benefit"),
                    row.get("period"),
                    row.get("documents"),
                    row.get("notes"),
                    row.get("source"),
                    bool(row.get("llm_used")),
                ),
            )
        for row in store.saved_policies.values():
            cur.execute(
                "INSERT INTO saved_policies(id,user_id,policy_id,saved_at) VALUES (%s,%s,%s,%s) ON CONFLICT (user_id, policy_id) DO NOTHING",
                (row["id"], row["user_id"], row["policy_id"], row.get("saved_at")),
            )
        for row in store.tax_documents.values():
            cur.execute(
                "INSERT INTO tax_documents(id,admin_id,title,law_name,content,source,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row.get("admin_id"),
                    row.get("title"),
                    row.get("law_name"),
                    row.get("content"),
                    row.get("source"),
                    row.get("created_at"),
                ),
            )
        for row in store.notifications.values():
            cur.execute(
                "INSERT INTO notifications(id,user_id,kind,title,body,channel,status,read_flag,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    row["id"],
                    row["user_id"],
                    row.get("kind"),
                    row.get("title"),
                    row.get("body"),
                    row.get("channel"),
                    row.get("status"),
                    bool(row.get("read")),
                    row.get("created_at"),
                ),
            )
        for name, value in store._next_ids.items():
            cur.execute("INSERT INTO meta_ids(name,value) VALUES (%s,%s)", (name, value))


def load_postgres(conn) -> None:
    from psycopg.rows import dict_row

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

    with conn.cursor(row_factory=dict_row) as cur:
        for item in cur.execute("SELECT * FROM admin_users"):
            store.admins[item["id"]] = dict(item)
            store.admins_by_email[item["email"]] = item["id"]
        for item in cur.execute("SELECT * FROM users"):
            row = dict(item)
            row["status"] = row.get("status") or "active"
            store.users[row["id"]] = row
            store.users_by_email[row["email"]] = row["id"]
        for item in cur.execute("SELECT * FROM business_profiles"):
            store.business_profiles[item["user_id"]] = dict(item)
        for item in cur.execute("SELECT * FROM chat_messages"):
            store.chat_messages[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM answer_sources"):
            store.answer_sources.setdefault(item["message_id"], []).append(
                {"title": item["title"], "url": item["url"], "excerpt": item["excerpt"]}
            )
        for item in cur.execute("SELECT * FROM tax_info"):
            store.tax_infos[item["user_id"]] = dict(item)
        for item in cur.execute("SELECT * FROM policies"):
            store.policies[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM calendar_events"):
            store.calendar_events[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM reminders"):
            row = dict(item)
            row["dispatched"] = bool(row.get("dispatched"))
            store.reminders[row["id"]] = row
        for item in cur.execute("SELECT * FROM tax_reduction_results"):
            reasons = item["reasons"]
            if isinstance(reasons, str):
                reasons = json.loads(reasons or "[]")
            store.tax_reduction_results[item["user_id"]] = {
                "id": item["id"],
                "eligible": bool(item["eligible"]),
                "reasons": reasons or [],
                "legalBasis": item["legal_basis"],
                "judged_at": item.get("judged_at"),
            }
        for item in cur.execute("SELECT * FROM receipts"):
            store.receipts[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM receipt_extractions"):
            items = item["items"]
            if isinstance(items, str):
                items = json.loads(items or "[]")
            store.receipt_extractions[item["receipt_id"]] = {
                "id": item["id"],
                "receipt_id": item["receipt_id"],
                "date": item["date"],
                "vendor": item["vendor"],
                "amount": item["amount"],
                "items": items or [],
            }
        for item in cur.execute("SELECT * FROM expenses"):
            store.expenses[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM announcements"):
            store.announcements[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM announcement_summaries"):
            store.announcement_summaries[item["announcement_id"]] = {
                **dict(item),
                "llm_used": bool(item.get("llm_used")),
            }
        for item in cur.execute("SELECT * FROM saved_policies"):
            store.saved_policies[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM tax_documents"):
            store.tax_documents[item["id"]] = dict(item)
        for item in cur.execute("SELECT * FROM notifications"):
            row = dict(item)
            row["read"] = bool(row.get("read_flag"))
            store.notifications[row["id"]] = row
        for item in cur.execute("SELECT * FROM meta_ids"):
            store._next_ids[item["name"]] = item["value"]
