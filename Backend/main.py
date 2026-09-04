from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import admin, auth, calendar, chat, expenses, policies, tax, users
from core.config import APP_DESCRIPTION, APP_NAME, APP_VERSION, OPENAPI_TAGS

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(calendar.router)
app.include_router(tax.router)
app.include_router(expenses.router)
app.include_router(policies.router)
app.include_router(admin.router)


@app.get("/health", tags=["상태"], summary="서버 상태 확인")
def health():
    """서버가 켜져 있는지 확인합니다. 저장은 메모리, LLM은 목업입니다."""
    return {"status": "ok", "storage": "memory", "llm": "mocked"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
