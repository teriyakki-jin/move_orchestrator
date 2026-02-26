from pydantic import BaseModel
from .task import TaskNode
from .service import ServiceCard
from .audit import AuditEvent


class ChatRequest(BaseModel):
    session_id: str = ""
    user_message: str


class NextQuestion(BaseModel):
    id: str
    question: str
    why: str
    options: list[str] = []
    optional: bool = True


class SuggestedAction(BaseModel):
    type: str  # "open_link" | "create_draft" | "call_center" | "visit_office"
    label: str
    payload: dict = {}


class ChatResponse(BaseModel):
    session_id: str
    assistant_message_markdown: str
    next_questions: list[NextQuestion] = []
    suggested_actions: list[SuggestedAction] = []
    service_cards: list[ServiceCard] = []
    task_graph: list[TaskNode] = []
    audit_events: list[AuditEvent] = []
    hitl_required: bool = False
    draft_id: str | None = None  # hitl_required=True일 때 submit 엔드포인트용
    draft_preview: dict | None = None  # 초안 필드 미리보기 (민감 필드 마스킹됨)
