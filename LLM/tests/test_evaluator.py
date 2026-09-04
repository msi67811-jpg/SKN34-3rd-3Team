import asyncio
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from src.evaluation.contracts import EvaluationCase, EvaluationObservation
from src.evaluation.evaluator import evaluate_cases


class FakeEvaluationClient:
    def __init__(self, observations: dict[int, EvaluationObservation]) -> None:
        self.observations = observations

    async def recommend(
        self,
        *,
        user_id: int,
        question: str,
        top_k: int,
    ) -> EvaluationObservation:
        del question, top_k
        return self.observations[user_id]


def test_evaluator_aggregates_retrieval_and_guardrail_metrics() -> None:
    cases = [
        EvaluationCase(
            case_id="retrieval",
            user_id=1,
            question="지원정책",
            relevant_policy_ids=[101, 102],
            should_block=False,
        ),
        EvaluationCase(
            case_id="blocked",
            user_id=2,
            question="날씨",
            relevant_policy_ids=[],
            should_block=True,
        ),
    ]
    client = FakeEvaluationClient(
        {
            1: EvaluationObservation(
                predicted_policy_ids=[101, 999, 102],
                guardrail_reason=None,
                latency_ms=10,
            ),
            2: EvaluationObservation(
                predicted_policy_ids=[],
                guardrail_reason="out_of_scope",
                latency_ms=20,
            ),
        }
    )

    report = asyncio.run(evaluate_cases(cases, client, k=3))

    assert report.summary.evaluated_cases == 2
    assert report.summary.retrieval_cases == 1
    assert report.summary.precision_at_k == pytest.approx(2 / 3)
    assert report.summary.recall_at_k == pytest.approx(1.0)
    assert report.summary.mrr == pytest.approx(1.0)
    assert report.summary.map == pytest.approx((1.0 + 2 / 3) / 2)
    assert report.summary.average_latency_ms == pytest.approx(15)
    assert report.summary.guardrail.accuracy == pytest.approx(1.0)
    assert report.cases[1].retrieval is None


def test_sample_dataset_matches_evaluation_contract() -> None:
    dataset_path = Path(__file__).parents[1] / "evaluation/sample_cases.json"
    cases = TypeAdapter(list[EvaluationCase]).validate_json(
        dataset_path.read_text(encoding="utf-8")
    )

    assert len(cases) == 5
    assert any(case.should_block for case in cases)
    assert any(case.relevant_policy_ids for case in cases)


def test_insufficient_evidence_is_counted_as_a_guardrail_block() -> None:
    cases = [
        EvaluationCase(
            case_id="missed-relevant-policy",
            user_id=1,
            question="지원정책",
            relevant_policy_ids=[101],
            should_block=False,
        )
    ]
    client = FakeEvaluationClient(
        {
            1: EvaluationObservation(
                predicted_policy_ids=[],
                guardrail_reason="insufficient_evidence",
                latency_ms=10,
            )
        }
    )

    report = asyncio.run(evaluate_cases(cases, client, k=5))

    assert report.cases[0].blocked is True
    assert report.summary.guardrail.false_positive == 1
