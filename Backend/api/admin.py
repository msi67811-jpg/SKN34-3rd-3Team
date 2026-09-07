from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_admin
from core import store
from core.database import persist
from core.llm_client import ensure_index, llm_status
from core.postgres import postgres_status
from schemas.auth import LoginRequest, LoginResponse
from services import auth_service

router = APIRouter(prefix="/admin", tags=["관리자"])


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def _serialize_user(user: dict) -> dict:
    profile = store.business_profiles.get(user["id"]) or {}
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "age": user.get("age"),
        "region": user.get("region"),
        "status": user.get("status") or "active",
        "createdAt": user.get("created_at"),
        "business": {
            "businessType": profile.get("business_type"),
            "industry": profile.get("industry"),
            "foundedAt": profile.get("founded_at"),
        },
    }


@router.post("/auth/login", response_model=LoginResponse, summary="관리자 로그인")
def admin_login(body: LoginRequest):
    return auth_service.admin_login(body.email, body.password)


@router.get("/users", summary="사용자 목록")
def list_users(_: dict = Depends(get_admin), page: int = Query(default=1, ge=1)):
    rows = list(store.users.values())
    start = (page - 1) * 20
    return {"users": [_serialize_user(user) for user in rows[start : start + 20]]}


@router.get("/users/{user_id}", summary="사용자 상세")
def user_detail(user_id: int, _: dict = Depends(get_admin)):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    chats = [m for m in store.chat_messages.values() if m["user_id"] == user_id]
    expenses = [e for e in store.expenses.values() if e["user_id"] == user_id]
    saved = [s for s in store.saved_policies.values() if s["user_id"] == user_id]
    return {
        "user": _serialize_user(user),
        "usage": {
            "chatMessages": len(chats),
            "expenses": len(expenses),
            "savedPolicies": len(saved),
        },
    }


@router.patch("/users/{user_id}", summary="사용자 상태 변경")
def update_user_status(user_id: int, body: dict, _: dict = Depends(get_admin)):
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    status = body.get("status")
    if status not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="status는 active 또는 suspended 입니다.")
    user["status"] = status
    persist()
    return {"user": _serialize_user(user)}


@router.get("/tax-documents", summary="세법 자료 목록")
def tax_documents(_: dict = Depends(get_admin)):
    return {"documents": list(store.tax_documents.values())}


@router.post("/tax-documents", summary="세법 자료 등록")
def create_tax_document(body: dict, current: dict = Depends(get_admin)):
    doc_id = store.next_id("taxdoc")
    store.tax_documents[doc_id] = {
        "id": doc_id,
        "admin_id": current["id"],
        "title": body.get("title"),
        "law_name": body.get("lawName"),
        "content": body.get("content"),
        "source": body.get("source"),
        "created_at": datetime.now(),
    }
    persist()
    return {"documentId": doc_id}


@router.get("/policies", summary="정책 데이터 목록")
def admin_policies(_: dict = Depends(get_admin)):
    return {"policies": list(store.policies.values())}


@router.post("/policies", summary="정책 데이터 등록")
def create_policy(body: dict, current: dict = Depends(get_admin)):
    pid = store.next_id("policy")
    start = _parse_date(body.get("applyStartDate"))
    end = _parse_date(body.get("applyEndDate"))
    store.policies[pid] = {
        "id": pid,
        "admin_id": current["id"],
        "title": body.get("title") or "제목 없음",
        "region": body.get("region") or "전국",
        "industry": body.get("industry") or "전 업종",
        "target": body.get("target") or "",
        "benefit": body.get("benefit") or body.get("content") or "",
        "eligibility_rule": body.get("eligibilityRule") or "",
        "source": body.get("source") or "",
        "created_at": datetime.now(),
    }
    aid = store.next_id("announcement")
    store.announcements[aid] = {
        "id": aid,
        "policy_id": pid,
        "raw_content": body.get("content") or body.get("benefit") or store.policies[pid]["title"],
        "source_url": body.get("sourceUrl") or body.get("source") or "",
        "apply_start_date": start,
        "apply_end_date": end,
        "apply_method": body.get("applyMethod") or "",
        "created_at": datetime.now(),
    }
    if end:
        eid = store.next_id("event")
        store.calendar_events[eid] = {
            "id": eid,
            "event_type": "POLICY",
            "business_type": None,
            "policy_id": pid,
            "title": f"{store.policies[pid]['title']} 신청 마감",
            "due_date": end,
            "description": f"{store.policies[pid].get('source') or ''} · {store.policies[pid]['region']}",
        }
    persist()
    return {"policyId": pid, "announcementId": aid}


@router.get("/announcements", summary="공고문 목록")
def admin_announcements(_: dict = Depends(get_admin)):
    return {"announcements": list(store.announcements.values())}


@router.post("/announcements", summary="공고문 등록")
def create_announcement(body: dict, _: dict = Depends(get_admin)):
    policy_id = body.get("policyId")
    if policy_id and policy_id not in store.policies:
        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
    aid = store.next_id("announcement")
    start = _parse_date(body.get("applyStartDate"))
    end = _parse_date(body.get("applyEndDate"))
    store.announcements[aid] = {
        "id": aid,
        "policy_id": policy_id,
        "raw_content": body.get("content") or body.get("title") or "",
        "source_url": body.get("sourceUrl") or "",
        "apply_start_date": start,
        "apply_end_date": end,
        "apply_method": body.get("applyMethod") or "",
        "created_at": datetime.now(),
    }
    if policy_id and end:
        eid = store.next_id("event")
        title = store.policies[policy_id]["title"]
        store.calendar_events[eid] = {
            "id": eid,
            "event_type": "POLICY",
            "business_type": None,
            "policy_id": policy_id,
            "title": f"{title} 신청 마감",
            "due_date": end,
            "description": store.policies[policy_id].get("source") or "",
        }
    persist()
    return {"announcementId": aid}


@router.post("/rag-documents/reindex", summary="RAG 문서 재색인")
def reindex(body: dict | None = None, _: dict = Depends(get_admin)):
    document_ids = (body or {}).get("documentIds")
    ok = ensure_index(document_ids)
    return {"status": "ready" if ok else "skipped", "llm": llm_status()}


@router.get("/monitoring", summary="시스템 모니터링")
def monitoring(_: dict = Depends(get_admin)):
    llm = llm_status()
    return {
        "metrics": {
            "users": len(store.users),
            "activeUsers": sum(1 for u in store.users.values() if (u.get("status") or "active") == "active"),
            "suspendedUsers": sum(1 for u in store.users.values() if u.get("status") == "suspended"),
            "policies": len(store.policies),
            "announcements": len(store.announcements),
            "taxDocuments": len(store.tax_documents),
            "chatMessages": len(store.chat_messages),
            "expenses": len(store.expenses),
            "reminders": len(store.reminders),
            "ragReady": bool(llm.get("ragReady")),
            "llm": llm,
            "postgres": postgres_status(),
        }
    }
