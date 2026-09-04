import hashlib

from core.config import TOKEN_PREFIX


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_token(user_id: int, role: str = "user") -> str:
    return f"{TOKEN_PREFIX}{role}_{user_id}"


def parse_token(token: str) -> tuple[str, int] | None:
    if not token.startswith(TOKEN_PREFIX):
        return None
    body = token[len(TOKEN_PREFIX) :]
    parts = body.rsplit("_", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return parts[0], int(parts[1])
