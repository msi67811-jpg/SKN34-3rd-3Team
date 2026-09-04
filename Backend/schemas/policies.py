from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PolicyItem(BaseModel):
    model_config = ConfigDict(title="지원정책")
    policyId: int = Field(description="정책 ID")
    title: str = Field(description="정책명")
    region: str = Field(description="지역")
    industry: str = Field(description="업종")
    target: str = Field(description="지원 대상")
    benefit: str = Field(description="지원 내용")
    source: str = Field(description="출처")
    applyEndDate: date | None = Field(default=None, description="신청 마감일")


class PolicyListResponse(BaseModel):
    model_config = ConfigDict(title="정책 목록")
    policies: list[PolicyItem] = Field(description="정책들")


class PolicyDetailResponse(BaseModel):
    model_config = ConfigDict(title="정책 상세")
    policy: PolicyItem = Field(description="정책 정보")
    applyPeriod: str = Field(description="신청 기간")
    applyMethod: str = Field(description="신청 방법")


class EligibilityResponse(BaseModel):
    model_config = ConfigDict(title="자격 확인 결과")
    eligible: bool = Field(description="충족 여부")
    reasons: list[str] = Field(description="판단 사유")


class AnnouncementSummaryResponse(BaseModel):
    model_config = ConfigDict(title="공고문 요약")
    target: str = Field(description="지원 대상")
    benefit: str = Field(description="지원 내용")
    period: str = Field(description="기간")
    documents: str = Field(description="제출 서류")
    notes: str = Field(description="유의사항")
    source: str = Field(description="출처")


class SavedResponse(BaseModel):
    model_config = ConfigDict(title="관심 저장 결과")
    saved: bool = Field(default=True, description="저장 여부")
