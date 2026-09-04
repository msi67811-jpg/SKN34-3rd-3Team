from fastapi import APIRouter, Depends, Query

from api.deps import get_current_user
from schemas.calendar import CalendarResponse
from services import calendar_service

router = APIRouter(prefix="/calendar", tags=["캘린더"])


@router.get("", response_model=CalendarResponse, summary="홈 화면 통합 캘린더")
def calendar(
    year: int | None = Query(default=None, description="연도"),
    month: int | None = Query(default=None, description="월 (1~12)"),
    type: str | None = Query(default=None, description="일정 종류: tax 또는 policy"),
    current: dict = Depends(get_current_user),
):
    """세금 신고일과 지원금 마감일을 한 번에 조회합니다."""
    _ = current
    return {"events": calendar_service.list_events(year, month, type)}
