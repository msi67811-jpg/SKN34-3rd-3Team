from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.core.config import Settings, get_settings
from src.rag.runtime import RagRuntime
from src.serving.app import create_app


def build_client(
    cache_path: Path,
    *,
    embedding_factory: Callable = lambda: DeterministicFakeEmbedding(size=32),
    llm_factory: Callable = lambda: FakeListChatModel(
        responses=["테스트 근거 답변입니다. [출처 1]"]
    ),
) -> TestClient:
    runtime = RagRuntime(
        embedding_factory=embedding_factory,
        llm_factory=llm_factory,
    )
    app = create_app(runtime=runtime)
    settings = Settings(
        _env_file=None,
        langsmith_tracing=False,
        min_relevance_score=0.0,
        chunk_size=500,
        chunk_overlap=50,
        embedding_model="test-embedding-model",
        vector_index_cache_path=cache_path,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_answer_requires_explicit_indexing(tmp_path: Path) -> None:
    client = build_client(tmp_path / "index.json")

    response = client.post(
        "/internal/rag/answer",
        json={"question": "지원 대상은 누구야?", "policy_id": 101},
    )

    assert response.status_code == 409
    assert "POST /internal/rag/index" in response.json()["detail"]


def test_index_ready_and_answer_flow_with_fake_models(tmp_path: Path) -> None:
    client = build_client(tmp_path / "index.json")

    index_response = client.post("/internal/rag/index")
    duplicate_response = client.post("/internal/rag/index")
    ready_response = client.get("/internal/rag/ready")
    answer_response = client.post(
        "/internal/rag/answer",
        json={
            "question": "초기창업 지원사업의 지원 대상은 누구야?",
            "policy_id": 101,
            "top_k": 2,
            "decision": {
                "eligible": True,
                "reasons": ["연령 조건 충족", "지역 조건 충족"],
            },
        },
    )

    assert index_response.status_code == 200
    index_body = index_response.json()
    assert index_body["status"] == "ready"
    assert index_body["source"] == "embedding"
    assert index_body["document_count"] == 5
    assert index_body["chunk_count"] > 0
    assert duplicate_response.json()["status"] == "already_ready"
    assert ready_response.json()["index_ready"] is True
    assert answer_response.status_code == 200
    body = answer_response.json()
    assert body["grounded"] is True
    assert body["sources"]
    assert all(source["policy_id"] == 101 for source in body["sources"])
    assert body["decision"] == {
        "eligible": True,
        "reasons": ["연령 조건 충족", "지역 조건 충족"],
    }


def test_new_server_runtime_loads_local_cache_without_reindexing(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "index.json"
    first_client = build_client(cache_path)
    assert first_client.post("/internal/rag/index").json()["source"] == "embedding"

    restarted_client = build_client(cache_path)
    response = restarted_client.post("/internal/rag/index")

    assert response.status_code == 200
    assert response.json()["source"] == "cache"


def test_health_does_not_create_embedding_or_llm(tmp_path: Path) -> None:
    calls = {"embedding": 0, "llm": 0}

    def embedding_factory() -> DeterministicFakeEmbedding:
        calls["embedding"] += 1
        return DeterministicFakeEmbedding(size=16)

    def llm_factory() -> FakeListChatModel:
        calls["llm"] += 1
        return FakeListChatModel(responses=["호출되면 안 됨"])

    client = build_client(
        tmp_path / "index.json",
        embedding_factory=embedding_factory,
        llm_factory=llm_factory,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert calls == {"embedding": 0, "llm": 0}


def test_personalized_policy_recommendation_uses_user_id_not_policy_input(
    tmp_path: Path,
) -> None:
    client = build_client(tmp_path / "index.json")
    client.post("/internal/rag/index")

    response = client.post(
        "/internal/rag/recommendations",
        json={
            "user_id": 1,
            "question": "내 조건과 관련된 지원정책을 알려줘",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 1
    assert body["grounded"] is True
    assert body["policies"]
    assert all(policy["sources"] for policy in body["policies"])


def test_unknown_mock_user_returns_not_found(tmp_path: Path) -> None:
    client = build_client(tmp_path / "index.json")
    client.post("/internal/rag/index")

    response = client.post(
        "/internal/rag/recommendations",
        json={"user_id": 999, "question": "관련 정책을 알려줘"},
    )

    assert response.status_code == 404
    assert "Mock user not found" in response.json()["detail"]


def test_unrelated_question_returns_guardrail_answer(tmp_path: Path) -> None:
    client = build_client(tmp_path / "index.json")
    client.post("/internal/rag/index")

    response = client.post(
        "/internal/rag/recommendations",
        json={"user_id": 1, "question": "오늘 날씨가 어때?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 1,
        "answer": "그 질문에는 답변할 수 없습니다",
        "grounded": False,
        "policies": [],
        "guardrail_reason": "out_of_scope",
    }


def test_mixed_domain_question_returns_guardrail_answer(tmp_path: Path) -> None:
    client = build_client(tmp_path / "index.json")
    client.post("/internal/rag/index")

    response = client.post(
        "/internal/rag/recommendations",
        json={
            "user_id": 1,
            "question": "나와 관련된 정책 알려줘 그리고 파이썬 append에 관해 알려줘",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "그 질문에는 답변할 수 없습니다"
    assert response.json()["policies"] == []
    assert response.json()["guardrail_reason"] == "out_of_scope"
