from langsmith import traceable

from src.data.contracts import UserProfile


@traceable(name="build_personalized_query", run_type="chain")
def build_personalized_query(question: str, user: UserProfile) -> str:
    """사용자 질문과 제공된 프로필 정보를 의미 검색용 Query로 결합한다.

    Args:
        question: 사용자가 입력한 정책 탐색 질문.
        user: 검색 개인화에 사용할 사용자·사업자 정보.

    Returns:
        질문과 누락되지 않은 프로필 필드를 결합한 검색 Query.
    """
    business_profile = user["business"]
    profile_descriptions = [
        _format_value("나이", user["age"], suffix="세"),
        _format_value("지역", user["region"]),
        _format_value("업종", business_profile["industry"]),
        _format_value("사업자 유형", business_profile["business_type"]),
        _format_value("창업일", business_profile["founded_at"]),
    ]
    available_profile_descriptions = [
        description
        for description in profile_descriptions
        if description is not None
    ]
    profile_context = (
        ", ".join(available_profile_descriptions) or "제공된 사용자 조건 없음"
    )
    return f"사용자 질문: {question}\n사용자 조건: {profile_context}"


def format_user_context(user: UserProfile) -> str:
    """사용자 프로필을 Prompt에 삽입할 읽기 쉬운 문자열로 변환한다.

    Args:
        user: 답변 개인화에 사용할 사용자·사업자 정보.

    Returns:
        각 프로필 필드를 한 줄씩 표현하고 누락값을 표시한 문자열.
    """
    business_profile = user["business"]
    return "\n".join(
        [
            f"나이: {_display_value(user['age'], suffix='세')}",
            f"지역: {_display_value(user['region'])}",
            f"업종: {_display_value(business_profile['industry'])}",
            f"사업자 유형: {_display_value(business_profile['business_type'])}",
            f"창업일: {_display_value(business_profile['founded_at'])}",
        ]
    )


def _format_value(label: str, value: object | None, *, suffix: str = "") -> str | None:
    """검색 Query용 프로필 필드를 누락값 없이 한 구절로 만든다."""
    if value is None or str(value).strip() == "":
        return None
    return f"{label} {value}{suffix}"


def _display_value(value: object | None, *, suffix: str = "") -> str:
    """Prompt 표시용 프로필 값을 변환하고 누락값을 명시한다."""
    if value is None or str(value).strip() == "":
        return "정보 없음"
    return f"{value}{suffix}"
