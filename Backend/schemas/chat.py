from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(title="챗봇 질문")
    category: str = Field(description="카테고리: tax / expense / saving / policy")
    question: str = Field(description="질문 내용")


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(title="챗봇 답변")
    messageId: int = Field(description="메시지 ID")
    answer: str = Field(description="답변 텍스트")
    grounded: bool = Field(default=False, description="RAG 근거가 있었는지")
    llmUsed: bool = Field(default=False, description="LLM 서비스 호출 여부")
    needsConfirmation: bool = Field(default=False, description="근거 부족으로 확인이 필요한지")


class SourceItem(BaseModel):
    model_config = ConfigDict(title="근거 문서")
    title: str = Field(description="문서 제목")
    url: str = Field(description="출처 URL")
    excerpt: str = Field(description="발췌 내용")


class SourcesResponse(BaseModel):
    model_config = ConfigDict(title="근거 문서 목록")
    sources: list[SourceItem] = Field(description="근거 문서들")


class SuggestedQuestionsResponse(BaseModel):
    model_config = ConfigDict(title="추천 질문")
    category: str = Field(description="카테고리")
    questions: list[str] = Field(description="추천 질문 목록")
