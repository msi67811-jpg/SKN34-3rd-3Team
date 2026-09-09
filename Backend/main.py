from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import admin, auth, calendar, chat, expenses, notifications, policies, tax, users
from core.config import APP_DESCRIPTION, APP_NAME, APP_VERSION, LLM_API_URL, OPENAPI_TAGS
from core.db import db_path, init_db, scalar
from core.llm_client import llm_status
from core.postgres import postgres_status

storage_mode = "pending"


@asynccontextmanager
async def lifespan(_: FastAPI):
    global storage_mode
    storage_mode = init_db()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
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
app.include_router(notifications.router)


@app.get("/health", tags=["상태"], summary="서버 상태 확인")
def health():
    llm = llm_status()
    postgres = postgres_status()
    policy_count = 0
    if storage_mode == "postgres":
        try:
            policy_count = int(scalar("SELECT COUNT(*) FROM policies") or 0)
        except Exception:
            policy_count = 0
    return {
        "status": "ok",
        "storage": storage_mode,
        "dbPath": db_path(),
        "postgres": "connected" if postgres["reachable"] else "unreachable",
        "pgvector": "ready" if postgres.get("pgvector") else "missing",
        "ragChunks": postgres.get("ragChunks", 0),
        "policies": policy_count,
        "llm": "connected" if llm["reachable"] else "unreachable",
        "ragReady": llm["ragReady"],
        "ports": {"backend": 8000, "llm": 8001},
        "llmUrl": LLM_API_URL,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
