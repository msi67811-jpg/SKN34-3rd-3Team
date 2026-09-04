from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.core.config import Settings, get_settings


class ModelConfigurationError(RuntimeError):
    """모델명 또는 OpenAI 인증정보가 없을 때 발생한다."""


def get_llm(settings: Settings | None = None) -> BaseChatModel:
    """환경설정에 지정된 OpenAI 채팅 모델 객체를 생성한다.

    Args:
        settings: 모델명과 API Key를 담은 설정. None이면 캐시된 환경설정을 사용한다.

    Returns:
        LangChain에서 호출할 수 있는 ChatOpenAI 객체.

    Raises:
        ModelConfigurationError: LLM 모델명 또는 OpenAI API Key가 없을 때.

    Notes:
        객체 생성만 수행하며 `invoke()` 또는 `ainvoke()` 전에는 API를 호출하지 않는다.
    """
    settings_config = settings or get_settings()
    if not settings_config.llm_configured:
        raise ModelConfigurationError(
            "LLM is not configured. Set LLM_MODEL and OPENAI_API_KEY in LLM/.env."
        )

    return ChatOpenAI(
        model=settings_config.llm_model,
        api_key=settings_config.openai_api_key,
        temperature=0,
    )


def get_embedding_model(settings: Settings | None = None) -> Embeddings:
    """환경설정에 지정된 OpenAI Embedding 모델 객체를 생성한다.

    Args:
        settings: 모델명과 API Key를 담은 설정. None이면 캐시된 환경설정을 사용한다.

    Returns:
        문서와 Query를 벡터화할 OpenAIEmbeddings 객체.

    Raises:
        ModelConfigurationError: Embedding 모델명 또는 OpenAI API Key가 없을 때.

    Notes:
        객체 생성만 수행하며 `embed_documents()` 또는 `embed_query()` 전에는 API를
        호출하지 않는다.
    """
    settings_config = settings or get_settings()
    if not settings_config.embedding_configured:
        raise ModelConfigurationError(
            "Embedding model is not configured. Set EMBEDDING_MODEL and "
            "OPENAI_API_KEY in LLM/.env."
        )
    return OpenAIEmbeddings(
        model=settings_config.embedding_model,
        api_key=settings_config.openai_api_key,
    )
