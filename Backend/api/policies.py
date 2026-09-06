from fastapi import APIRouter, Depends, Path, Query

from api.deps import get_current_user
from schemas.policies import (
    AnnouncementSummaryResponse,
    EligibilityResponse,
    PolicyDetailResponse,
    PolicyListResponse,
    SavedResponse,
)
from services import policy_service

router = APIRouter(tags=["지원정책"])


@router.get("/policies", response_model=PolicyListResponse, summary="지원정책 검색")
def search(
    keyword: str | None = Query(default=None, description="검색 키워드"),
    region: str | None = Query(default=None, description="지역 (예: 서울)"),
    industry: str | None = Query(default=None, description="업종"),
    current: dict = Depends(get_current_user),
):
    """키워드·지역·업종으로 샘플 정책을 검색합니다."""
    return {"policies": policy_service.search(keyword, region, industry, current["id"])}


@router.get(
    "/policies/recommendations",
    response_model=PolicyListResponse,
    summary="맞춤 정책 추천",
)
def recommendations(current: dict = Depends(get_current_user)):
    """온보딩 프로필과 정책 요건을 비교해 추천합니다."""
    return {"policies": policy_service.recommendations(current["id"])}


@router.get("/policies/saved", response_model=PolicyListResponse, summary="관심 정책 목록")
def saved(current: dict = Depends(get_current_user)):
    """저장한 관심 정책 목록입니다."""
    return {"policies": policy_service.saved_list(current["id"])}


@router.get("/policies/{policy_id}", response_model=PolicyDetailResponse, summary="정책 상세")
def detail(
    policy_id: int = Path(description="정책 ID"),
    current: dict = Depends(get_current_user),
):
    """신청기간·신청방법을 포함한 정책 상세입니다."""
    _ = current
    return policy_service.detail(policy_id)


@router.get(
    "/policies/{policy_id}/eligibility",
    response_model=EligibilityResponse,
    summary="지원 자격 확인",
)
def eligibility(
    policy_id: int = Path(description="정책 ID"),
    current: dict = Depends(get_current_user),
):
    """내 프로필과 정책 요건을 비교합니다."""
    return policy_service.eligibility(policy_id, current["id"])


@router.post(
    "/policies/{policy_id}/save",
    response_model=SavedResponse,
    summary="관심 정책 저장",
)
def save(
    policy_id: int = Path(description="정책 ID"),
    current: dict = Depends(get_current_user),
):
    policy_service.save_policy(current["id"], policy_id)
    return {"saved": True}


@router.get(
    "/announcements/{announcement_id}/summary",
    response_model=AnnouncementSummaryResponse,
    summary="공고문 요약 조회",
)
def summary(
    announcement_id: int = Path(description="공고 ID"),
    current: dict = Depends(get_current_user),
):
    """저장된 요약이 있으면 쓰고, LLM 서비스가 있으면 다시 요약합니다."""
    _ = current
    return policy_service.announcement_summary(announcement_id)
