from collections.abc import Iterable, Sequence
from typing import Protocol

from src.evaluation.contracts import (
    CaseEvaluation,
    EvaluationCase,
    EvaluationObservation,
    EvaluationReport,
    EvaluationSummary,
)
from src.evaluation.metrics import guardrail_metrics, retrieval_metrics


class RecommendationEvaluationClient(Protocol):
    """정책 추천 결과를 평가기에 제공하는 비동기 Client 계약."""

    async def recommend(
        self,
        *,
        user_id: int,
        question: str,
        top_k: int,
    ) -> EvaluationObservation:
        """질문을 실행하고 평가에 필요한 관찰값을 반환한다.

        Args:
            user_id: 평가 질문에 사용할 사용자 식별자.
            question: 검색·Guardrail을 평가할 사용자 질문.
            top_k: 정책 검색에 사용할 최대 결과 개수.

        Returns:
            예측 정책 순위, Guardrail 사유와 응답 시간을 담은 관찰값.
        """
        ...


async def evaluate_cases(
    cases: Sequence[EvaluationCase],
    client: RecommendationEvaluationClient,
    *,
    k: int,
) -> EvaluationReport:
    """평가 케이스를 실행하고 검색·Guardrail 평균 지표를 계산한다.

    Args:
        cases: 질문, 정답 정책 ID와 차단 기대값이 정의된 평가 케이스.
        client: 현재 Mock 또는 향후 실제 API 결과를 제공할 평가 Client.
        k: 검색 결과를 평가할 상위 정책 개수.

    Returns:
        전체 평균 지표와 케이스별 상세 결과를 포함한 평가 보고서.

    Raises:
        ValueError: k가 1보다 작을 때.

    Notes:
        검색 지표는 정답 정책이 있는 허용 질문만 평균내며, Guardrail은 모든
        케이스를 대상으로 평가한다.
    """
    if k < 1:
        raise ValueError("k must be at least 1")

    case_evaluations: list[CaseEvaluation] = []
    retrieval_metric_results = []
    expected_block_labels = []
    predicted_block_labels = []

    for evaluation_case in cases:
        observed_result = await client.recommend(
            user_id=evaluation_case.user_id,
            question=evaluation_case.question,
            top_k=k,
        )
        was_blocked = observed_result.guardrail_reason is not None
        expected_block_labels.append(evaluation_case.should_block)
        predicted_block_labels.append(was_blocked)

        case_retrieval_metrics = None
        if evaluation_case.relevant_policy_ids and not evaluation_case.should_block:
            case_retrieval_metrics = retrieval_metrics(
                observed_result.predicted_policy_ids,
                set(evaluation_case.relevant_policy_ids),
                k,
            )
            retrieval_metric_results.append(case_retrieval_metrics)

        case_evaluations.append(
            CaseEvaluation(
                case_id=evaluation_case.case_id,
                predicted_policy_ids=observed_result.predicted_policy_ids,
                relevant_policy_ids=evaluation_case.relevant_policy_ids,
                should_block=evaluation_case.should_block,
                blocked=was_blocked,
                guardrail_reason=observed_result.guardrail_reason,
                retrieval=case_retrieval_metrics,
                latency_ms=observed_result.latency_ms,
            )
        )

    evaluation_summary = EvaluationSummary(
        k=k,
        evaluated_cases=len(cases),
        retrieval_cases=len(retrieval_metric_results),
        precision_at_k=_mean(
            metrics.precision_at_k for metrics in retrieval_metric_results
        ),
        recall_at_k=_mean(
            metrics.recall_at_k for metrics in retrieval_metric_results
        ),
        mrr=_mean(
            metrics.reciprocal_rank for metrics in retrieval_metric_results
        ),
        map=_mean(
            metrics.average_precision for metrics in retrieval_metric_results
        ),
        average_latency_ms=_mean(
            case_evaluation.latency_ms for case_evaluation in case_evaluations
        ),
        guardrail=guardrail_metrics(
            expected_block_labels,
            predicted_block_labels,
        ),
    )
    return EvaluationReport(summary=evaluation_summary, cases=case_evaluations)


def _mean(values: Iterable[float]) -> float:
    """평가값 Iterable의 산술평균을 계산하고 빈 입력에는 0을 반환한다."""
    metric_values = list(values)
    return sum(metric_values) / len(metric_values) if metric_values else 0.0
