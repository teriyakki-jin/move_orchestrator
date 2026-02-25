from fastapi import APIRouter, HTTPException
from ..schemas.api_models import ChatRequest, ChatResponse
from ..orchestrator.orchestrator import Orchestrator

router = APIRouter()
_orchestrator = Orchestrator()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.user_message.strip():
        raise HTTPException(status_code=400, detail="메시지를 입력해 주세요.")
    return _orchestrator.handle_turn(
        session_id=request.session_id,
        user_message=request.user_message,
    )


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = _orchestrator.session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return session.model_dump()
