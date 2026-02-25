from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.chat import router as chat_router
from .api.chat_mock import router as chat_mock_router
from .api.health import router as health_router
from .api.submit import router as submit_router
from .core.config import get_settings

app = FastAPI(
    title="이사 AI 민원 오케스트레이터",
    description="이사 이벤트 기반 AI 민원 MVP",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["health"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(chat_mock_router, prefix="/api/v1", tags=["chat-mock"])
app.include_router(submit_router, prefix="/api/v1", tags=["submit"])


@app.on_event("startup")
def startup():
    settings = get_settings()
    print(f"[startup] OpenAI 모델: {settings.openai_model}")
