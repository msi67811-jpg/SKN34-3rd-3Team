from datetime import date

from fastapi import HTTPException

from core import store
from core.database import persist
from core.llm_client import summarize_announcement


def _announcement_of(policy_id: int) -> dict | None:
    return next((a for a in store.announcements.values() if a["policy_id"] == policy_id), None)


def _to_item(policy: dict, *, match_score: int | None = None, eligible: bool | None = None) -> dict:
    announcement = _announcement_of(policy["id"])
    return {
        "policyId": policy["id"],
        "title": policy["title"],
        "region": policy["region"],
        "industry": policy["industry"],
        "target": policy["target"],
        "benefit": policy["benefit"],
        "source": policy["source"],
        "applyEndDate": announcement["apply_end_date"] if announcement else None,
        "matchScore": match_score,
        "eligible": eligible,
    }


def _to_item_for_user(policy: dict, user_id: int | None) -> dict:
    if not user_id:
        return _to_item(policy)
    user = store.users.get(user_id) or {}
    profile = store.business_profiles.get(user_id) or {}
    score, ok, _ = _score_policy(policy, user, profile)
    return _to_item(policy, match_score=score, eligible=ok)


def search(keyword: str | None, region: str | None, industry: str | None, user_id: int | None = None) -> list[dict]:
    rows = list(store.policies.values())
    if keyword:
        rows = [p for p in rows if keyword in p["title"] or keyword in p["benefit"]]
    if region:
        rows = [p for p in rows if p["region"] in (region, "전국")]
    if industry:
        rows = [p for p in rows if p["industry"] in (industry, "전 업종")]
    items = [_to_item_for_user(p, user_id) for p in rows]
    items.sort(key=lambda item: (item.get("eligible") or False, item.get("matchScore") or 0), reverse=True)
    return items


def _years_since(founded: date | None) -> float | None:
    if not founded:
        return None
    return (date.today() - founded).days / 365


def _match_rule(rule: str, user: dict, profile: dict) -> tuple[bool, list[str]]:
    reasons = []
    ok = True
    age = user.get("age")
    region = user.get("region")
    founded_years = _years_since(profile.get("founded_at"))
    for token in rule.split(","):
        token = token.strip()
        if token.startswith("age<=") and age is not None:
            limit = int(token.split("=")[1])
            hit = age <= limit
            ok = ok and hit
            reasons.append(f"나이 {age}세 / 요건 {token}: {'충족' if hit else '미충족'}")
        elif token.startswith("region=") and region:
            need = token.split("=", 1)[1]
            hit = region == need
            ok = ok and hit
            reasons.append(f"지역 {region} / 요건 {need}: {'충족' if hit else '미충족'}")
        elif token.startswith("founded_years<=") and founded_years is not None:
            limit = float(token.split("=")[1])
            hit = founded_years <= limit
            ok = ok and hit
            reasons.append(f"업력 {founded_years:.1f}년 / 요건 {token}: {'충족' if hit else '미충족'}")
        elif token.startswith("business_type!="):
            banned = token.split("!=", 1)[1]
            current = profile.get("business_type") or "미등록"
            hit = current != banned
            ok = ok and hit
            reasons.append(f"사업자 유형 {current}: {'충족' if hit else '미충족'}")
    if not reasons:
        reasons.append("상세 프로필이 부족해 참고용으로만 표시합니다.")
    return ok, reasons


def _score_policy(policy: dict, user: dict, profile: dict) -> tuple[int, bool, list[str]]:
    ok, reasons = _match_rule(policy.get("eligibility_rule") or "", user, profile)
    score = 20 if ok else 0
    region = user.get("region")
    industry = profile.get("industry")
    if policy.get("region") in (region, "전국") or not region:
        score += 30
    if policy.get("industry") in (industry, "전 업종") or not industry:
        score += 25
    announcement = _announcement_of(policy["id"])
    if announcement and announcement.get("apply_end_date"):
        remaining = (announcement["apply_end_date"] - date.today()).days
        if 0 <= remaining <= 30:
            score += 15
        elif remaining < 0:
            score -= 20
    return max(score, 0), ok, reasons


def recommendations(user_id: int) -> list[dict]:
    user = store.users.get(user_id) or {}
    profile = store.business_profiles.get(user_id) or {}
    ranked = []
    for policy in store.policies.values():
        score, ok, _ = _score_policy(policy, user, profile)
        ranked.append(_to_item(policy, match_score=score, eligible=ok))
    ranked.sort(key=lambda item: (item.get("eligible") or False, item.get("matchScore") or 0), reverse=True)
    preferred = [item for item in ranked if item.get("eligible") or (item.get("matchScore") or 0) >= 40]
    return preferred or ranked[:3]


def detail(policy_id: int) -> dict:
    policy = store.policies.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
    announcement = _announcement_of(policy_id)
    period = ""
    method = ""
    if announcement:
        period = f"{announcement['apply_start_date']} ~ {announcement['apply_end_date']}"
        method = announcement.get("apply_method", "")
    return {
        "policy": _to_item(policy),
        "applyPeriod": period,
        "applyMethod": method,
        "announcementId": announcement["id"] if announcement else None,
    }


def eligibility(policy_id: int, user_id: int) -> dict:
    policy = store.policies.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
    user = store.users.get(user_id) or {}
    profile = store.business_profiles.get(user_id) or {}
    ok, reasons = _match_rule(policy["eligibility_rule"], user, profile)
    return {"eligible": ok, "reasons": reasons}


def save_policy(user_id: int, policy_id: int) -> None:
    if policy_id not in store.policies:
        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
    for saved in store.saved_policies.values():
        if saved["user_id"] == user_id and saved["policy_id"] == policy_id:
            return
    key = store.next_id("saved")
    store.saved_policies[key] = {
        "id": key,
        "user_id": user_id,
        "policy_id": policy_id,
        "saved_at": __import__("datetime").datetime.now(),
    }
    persist()


def saved_list(user_id: int) -> list[dict]:
    ids = [s["policy_id"] for s in store.saved_policies.values() if s["user_id"] == user_id]
    items = [_to_item_for_user(store.policies[pid], user_id) for pid in ids if pid in store.policies]
    items.sort(key=lambda item: (item.get("eligible") or False, item.get("matchScore") or 0), reverse=True)
    return items


def announcement_summary(announcement_id: int) -> dict:
    announcement = store.announcements.get(announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다.")
    cached = store.announcement_summaries.get(announcement_id)
    if cached:
        return {
            "target": cached["target"],
            "benefit": cached["benefit"],
            "period": cached["period"],
            "documents": cached["documents"],
            "notes": cached["notes"],
            "source": cached["source"],
            "llmUsed": bool(cached.get("llm_used")),
        }
    llm = summarize_announcement(announcement.get("raw_content") or "", announcement.get("source_url"))
    if llm and llm.get("benefit"):
        summary = {
            "id": (cached or {}).get("id") or store.next_id("summary"),
            "announcement_id": announcement_id,
            "target": llm.get("target") or "",
            "benefit": llm.get("benefit") or "",
            "period": llm.get("period") or "",
            "documents": llm.get("documents") or "",
            "notes": llm.get("notes") or "",
            "source": llm.get("source") or announcement.get("source_url") or "",
            "llm_used": bool(llm.get("llmUsed")),
        }
        store.announcement_summaries[announcement_id] = summary
        persist()
        cached = summary
    if not cached:
        raise HTTPException(status_code=404, detail="공고 요약을 찾을 수 없습니다.")
    return {
        "target": cached["target"],
        "benefit": cached["benefit"],
        "period": cached["period"],
        "documents": cached["documents"],
        "notes": cached["notes"],
        "source": cached["source"],
        "llmUsed": bool(cached.get("llm_used")),
    }
