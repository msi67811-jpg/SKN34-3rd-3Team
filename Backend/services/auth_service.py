from fastapi import HTTPException

from core import store
from core.database import persist
from core.security import create_token, hash_password, verify_password


def signup(email: str, password: str, name: str) -> int:
    if email in store.users_by_email:
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.")
    user = {
        "id": store.next_id("user"),
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "age": None,
        "region": None,
        "phone": "",
        "status": "active",
        "created_at": __import__("datetime").datetime.now(),
    }
    store.users[user["id"]] = user
    store.users_by_email[email] = user["id"]
    persist()
    return user["id"]


def login(email: str, password: str) -> dict:
    uid = store.users_by_email.get(email)
    if uid is None:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    user = store.users[uid]
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="정지된 계정입니다. 관리자에게 문의하세요.")
    return {
        "accessToken": create_token(user["id"], "user"),
        "userId": user["id"],
        "name": user["name"],
        "role": "user",
    }


def admin_login(email: str, password: str) -> dict:
    aid = store.admins_by_email.get(email)
    if aid is None:
        raise HTTPException(status_code=401, detail="관리자 인증에 실패했습니다.")
    admin = store.admins[aid]
    if not verify_password(password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="관리자 인증에 실패했습니다.")
    return {
        "accessToken": create_token(admin["id"], "admin"),
        "userId": admin["id"],
        "name": "관리자",
        "role": "admin",
    }
