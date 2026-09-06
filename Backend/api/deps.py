from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core import store
from core.security import parse_token

bearer = HTTPBearer(auto_error=False, description="로그인 응답의 accessToken을 Bearer로 넣습니다.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    parsed = parse_token(credentials.credentials)
    if not parsed:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    role, uid = parsed
    if role == "admin":
        admin = store.admins.get(uid)
        if not admin:
            raise HTTPException(status_code=401, detail="관리자를 찾을 수 없습니다.")
        return {"id": uid, "role": "admin", "email": admin["email"]}
    user = store.users.get(uid)
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    if user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="정지된 계정입니다.")
    return {**user, "role": "user"}


def get_admin(current: dict = Depends(get_current_user)) -> dict:
    if current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return current
