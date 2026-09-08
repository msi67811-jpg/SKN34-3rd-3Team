import argparse
import asyncio
from pathlib import Path
from time import perf_counter

from httpx import AsyncClient
from pydantic import TypeAdapter

from src.evaluation.evaluator import (
    EvaluationCase,
    EvaluationObservation,
    evaluate_cases,
)


PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_DIR / "evaluation/sample_cases.json"
DEFAULT_OUTPUT = PROJECT_DIR / "evaluation/results/latest_report.json"


class HttpRecommendationClient:
    """현재 내부 정책 추천 API를 평가기에 연결하는 HTTP adapter."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 60.0) -> None:
        """평가용 비동기 HTTP Client를 초기화한다.

        Args:
            base_url: 실행 중인 LLM FastAPI 서버의 기본 URL.
            timeout_seconds: 평가 요청 한 건의 최대 대기 시간.
        """
        self._client = AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
        )

    async def __aenter__(self) -> "HttpRecommendationClient":
        """async with 문에서 현재 Client를 반환한다."""
        return self

    async def __aexit__(self, *_args: object) -> None:
        """async with 문을 종료할 때 HTTP 연결을 닫는다."""
        await self._client.aclose()

    async def prepare_index(self) -> None:
        """평가 전에 서버 프로세스의 RAG 인덱스를 준비한다."""
        index_response = await self._client.post("/internal/rag/index")
        index_response.raise_for_status()

    async def recommend(
        self,
        *,
        user_id: int,
        question: str,
        top_k: int,
    ) -> EvaluationObservation:
        """정책 추천 API 응답을 평가에 필요한 관찰값으로 변환한다.

        Args:
            user_id: 평가 질문에 사용할 사용자 식별자.
            question: 검색·Guardrail을 평가할 사용자 질문.
            top_k: 정책 검색에 사용할 최대 결과 개수.

        Returns:
            예측 정책 순위, Guardrail 사유와 응답 시간을 담은 관찰값.
        """
        request_started_at = perf_counter()
        recommendation_response = await self._client.post(
            "/internal/rag/recommendations",
            json={"user_id": user_id, "question": question, "top_k": top_k},
        )
        response_latency_ms = (perf_counter() - request_started_at) * 1000
        recommendation_response.raise_for_status()
        response_body = recommendation_response.json()
        return EvaluationObservation(
            predicted_policy_ids=[
                int(policy["policy_id"])
                for policy in response_body.get("policies", [])
            ],
            guardrail_reason=response_body.get("guardrail_reason"),
            latency_ms=response_latency_ms,
        )


def build_parser() -> argparse.ArgumentParser:
    """검색·Guardrail 평가 CLI argument parser를 생성한다.

    Returns:
        평가셋, 출력 경로, API URL, k와 인덱스 준비 옵션이 등록된 parser.
    """
    argument_parser = argparse.ArgumentParser(
        description="Evaluate policy retrieval and scope guardrails."
    )
    argument_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    argument_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    argument_parser.add_argument("--base-url", default="http://localhost:8000")
    argument_parser.add_argument("--k", type=int, default=5)
    argument_parser.add_argument(
        "--prepare-index",
        action="store_true",
        help="Load the local vector cache before evaluation",
    )
    return argument_parser


async def run_evaluation(cli_arguments: argparse.Namespace) -> None:
    """평가셋으로 RAG API를 실행하고 JSON 보고서를 저장한다.

    Args:
        cli_arguments: CLI에서 받은 평가셋·출력 경로·API URL·k 설정.

    Notes:
        실제 API를 대상으로 실행하면 Query Embedding과 LLM 비용이 발생할 수 있다.
    """
    evaluation_cases = TypeAdapter(list[EvaluationCase]).validate_json(
        cli_arguments.dataset.read_text(encoding="utf-8")
    )
    async with HttpRecommendationClient(cli_arguments.base_url) as evaluation_client:
        if cli_arguments.prepare_index:
            await evaluation_client.prepare_index()
        evaluation_report = await evaluate_cases(
            evaluation_cases,
            evaluation_client,
            k=cli_arguments.k,
        )

    report_json = evaluation_report.model_dump_json(indent=2)
    cli_arguments.output.parent.mkdir(parents=True, exist_ok=True)
    cli_arguments.output.write_text(report_json, encoding="utf-8")
    print(report_json)
    print(f"Saved report to: {cli_arguments.output}")


def main() -> None:
    """CLI 입력을 검증하고 비동기 평가 실행기를 시작한다."""
    cli_arguments = build_parser().parse_args()
    if cli_arguments.k < 1:
        raise SystemExit("--k must be at least 1")
    try:
        asyncio.run(run_evaluation(cli_arguments))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Evaluation failed: {exc}") from exc


if __name__ == "__main__":
    main()
