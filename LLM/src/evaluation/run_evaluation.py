import argparse
import asyncio
from pathlib import Path

from pydantic import TypeAdapter

from src.evaluation.contracts import EvaluationCase
from src.evaluation.evaluator import evaluate_cases
from src.evaluation.http_client import HttpRecommendationClient


PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_DIR / "evaluation/sample_cases.json"
DEFAULT_OUTPUT = PROJECT_DIR / "evaluation/results/latest_report.json"


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
