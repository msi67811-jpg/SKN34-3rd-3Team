import pytest

from src.core.config import Settings
from src.models import ModelConfigurationError, get_embedding_model, get_llm


def test_llm_factory_rejects_missing_configuration() -> None:
    with pytest.raises(ModelConfigurationError, match="LLM is not configured"):
        get_llm(Settings(_env_file=None))


def test_embedding_factory_rejects_missing_configuration() -> None:
    with pytest.raises(ModelConfigurationError, match="Embedding model is not configured"):
        get_embedding_model(Settings(_env_file=None))
