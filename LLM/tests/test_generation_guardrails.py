import pytest

from src.data import get_rag_chunks
from src.rag.guardrails import (
    GenerationValidationError,
    validate_citation_numbers,
    validate_generated_policy_ids,
    validate_generated_text,
    validate_policy_citations,
)


def test_citation_numbers_are_deduplicated_in_original_order() -> None:
    assert validate_citation_numbers([2, 1, 2], source_count=2) == (2, 1)


@pytest.mark.parametrize("citations", [[], [0], [3]])
def test_missing_or_invalid_citation_numbers_are_rejected(citations: list[int]) -> None:
    with pytest.raises(GenerationValidationError):
        validate_citation_numbers(citations, source_count=2)


def test_generated_policy_ids_must_exist_in_retrieved_context() -> None:
    assert validate_generated_policy_ids(
        [101, 102],
        retrieved_policy_ids={101, 102},
    ) == (101, 102)

    with pytest.raises(GenerationValidationError, match="not retrieved"):
        validate_generated_policy_ids([999], retrieved_policy_ids={101, 102})


def test_policy_citation_must_point_to_the_same_policy() -> None:
    policy_101_chunk = get_rag_chunks()[0].copy()
    policy_102_chunk = get_rag_chunks()[2].copy()
    policy_101_chunk["score"] = 0.9
    policy_102_chunk["score"] = 0.8

    with pytest.raises(GenerationValidationError, match="another policy"):
        validate_policy_citations(
            101,
            (2,),
            (policy_101_chunk, policy_102_chunk),
        )


def test_blank_generated_text_is_rejected() -> None:
    with pytest.raises(GenerationValidationError, match="must not be blank"):
        validate_generated_text("   ", field_name="answer")
