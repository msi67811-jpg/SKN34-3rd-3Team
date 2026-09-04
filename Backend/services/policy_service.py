from datetime import date

from fastapi import HTTPException

from core import store


def _announcement_of(policy_id: int) -> dict | None:
    return next((a for a in store.announcements.values() if a["policy_id"] == policy_id), None)


def _to_item(policy: dict) -> dict:
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
    }


def search(keyword: str | None, region: str | None, industry: str | None) -> list[dict]:
    rows = list(store.policies.values())
    if keyword:
        rows = [p for p in rows if keyword in p["title"] or keyword in p["benefit"]]
    if region:
        rows = [p for p in rows if p["region"] in (region, "전국")]
    if industry:
        rows = [p for p in rows if p["industry"] in (industry, "전 업종")]
    return [_to_item(p) for p in rows]


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


def recommendations(user_id: int) -> list[dict]:
    user = store.users.get(user_id) or {}
    profile = store.business_profiles.get(user_id) or {}
    matched = []
    for policy in store.policies.values():
        ok, _ = _match_rule(policy["eligibility_rule"], user, profile)
        if ok:
            matched.append(_to_item(policy))
    return matched or [_to_item(p) for p in list(store.policies.values())[:3]]


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
    key = store.next_id("saved")
    store.saved_policies[key] = {
        "id": key,
        "user_id": user_id,
        "policy_id": policy_id,
        "saved_at": __import__("datetime").datetime.now(),
    }


def saved_list(user_id: int) -> list[dict]:
    ids = [s["policy_id"] for s in store.saved_policies.values() if s["user_id"] == user_id]
    return [_to_item(store.policies[pid]) for pid in ids if pid in store.policies]


def announcement_summary(announcement_id: int) -> dict:
    summary = store.announcement_summaries.get(announcement_id)
    if not summary:
        raise HTTPException(status_code=404, detail="공고 요약을 찾을 수 없습니다.")
    return {
        "target": summary["target"],
        "benefit": summary["benefit"],
        "period": summary["period"],
        "documents": summary["documents"],
        "notes": summary["notes"],
        "source": summary["source"],
    }
