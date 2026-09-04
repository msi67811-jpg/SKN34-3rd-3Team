from typing import Literal

from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    """질문별 기대 정책과 Guardrail 정답을 정의한 평가 케이스."""

    case_id: str
    user_id: int
    question: str
    relevant_policy_ids: list[int]
    should_block: bool


class EvaluationObservation(BaseModel):
    """RAG API에서 관찰한 정책 순위·차단 사유·응답 시간."""

    predicted_policy_ids: list[int]
    guardrail_reason: Literal["out_of_scope", "insufficient_evidence"] | None
    latency_ms: float = Field(ge=0)


class RetrievalMetrics(BaseModel):
    """평가 케이스 한 건의 P@k, R@k, RR과 AP@k."""

    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    average_precision: float


class GuardrailMetrics(BaseModel):
    """차단을 Positive로 정의한 Guardrail 이진 분류 지표."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int


class CaseEvaluation(BaseModel):
    """기대값과 관찰값을 비교한 평가 케이스별 상세 결과."""

    case_id: str
    predicted_policy_ids: list[int]
    relevant_policy_ids: list[int]
    should_block: bool
    blocked: bool
    guardrail_reason: str | None
    retrieval: RetrievalMetrics | None
    latency_ms: float


class EvaluationSummary(BaseModel):
    """전체 평가셋의 검색·Guardrail 평균 지표와 응답 시간."""

    k: int
    evaluated_cases: int
    retrieval_cases: int
    precision_at_k: float
    recall_at_k: float
    mrr: float
    map: float
    average_latency_ms: float
    guardrail: GuardrailMetrics


class EvaluationReport(BaseModel):
    """평가 요약과 모든 케이스 상세 결과를 포함한 최종 보고서."""

    summary: EvaluationSummary
    cases: list[CaseEvaluation]
