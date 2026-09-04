from time import perf_counter

from httpx import AsyncClient

from src.evaluation.contracts import EvaluationObservation


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
        """평가 전에 서버 프로세스의 RAG 인덱스를 준비한다.

        Notes:
            유효한 로컬 캐시가 없으면 문서 Embedding API가 호출될 수 있다.
        """
        index_response = await self._client.post("/internal/rag/index")
        index_response.raise_for_status()

    async def recommend(
        self,
        *,
        user_id: int,
        question: str,
        top_k: int,
    ) -> EvaluationObservation:
        """정책 추천 API를 호출하고 평가에 필요한 관찰값으로 변환한다.

        Args:
            user_id: Mock 또는 실제 사용자 프로필을 조회할 식별자.
            question: 정책 검색과 Guardrail 평가에 사용할 사용자 질문.
            top_k: API에 요청할 최대 검색 Chunk 개수.

        Returns:
            정책 ID 순위, Guardrail 차단 사유와 전체 응답 시간.

        Notes:
            허용 질문은 Query Embedding과 LLM API 호출이 발생할 수 있다.
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
