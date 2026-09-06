from fastapi import HTTPException

from core import store
from core.database import persist


def get_me(user_id: int) -> dict:
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "age": user.get("age"),
        "region": user.get("region"),
        "phone": user.get("phone") or "",
    }


def update_me(user_id: int, payload: dict) -> None:
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    for key in ("name", "age", "region", "phone"):
        if payload.get(key) is not None:
            user[key] = payload[key]
    persist()


def get_business_profile(user_id: int) -> dict:
    profile = store.business_profiles.get(user_id)
    if not profile:
        return {
            "businessType": None,
            "industry": None,
            "businessRegisteredAt": None,
            "foundedAt": None,
        }
    return {
        "businessType": profile.get("business_type"),
        "industry": profile.get("industry"),
        "businessRegisteredAt": profile.get("business_registered_at"),
        "foundedAt": profile.get("founded_at"),
    }


def update_business_profile(user_id: int, payload: dict) -> None:
    profile = store.business_profiles.get(user_id) or {
        "id": store.next_id("biz"),
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
            profile[dest] = payload[src]
    store.business_profiles[user_id] = profile
    persist()


def onboarding_complete(user_id: int) -> bool:
    user = store.users.get(user_id) or {}
    profile = store.business_profiles.get(user_id) or {}
    return bool(user.get("age") and user.get("region") and profile.get("business_type"))
