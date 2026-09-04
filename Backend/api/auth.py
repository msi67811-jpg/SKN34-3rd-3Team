from fastapi import APIRouter

from schemas.auth import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse)
def signup(body: SignupRequest):
    user_id = auth_service.signup(body.email, body.password, body.name)
    return {"userId": user_id}


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    return auth_service.login(body.email, body.password)


@router.post("/logout")
def logout():
    return {}
