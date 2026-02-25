import re
from pydantic import BaseModel
from .base import BaseAgent
from ..prompts import SAFETY_PROMPT
from ..schemas.audit import AuditEvent

_PII_PATTERNS = [
    (re.compile(r"\d{6}-[1-4]\d{6}"), "주민등록번호"),
    (re.compile(r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"), "카드번호"),
    (re.compile(r"\d{10,14}"), "계좌번호 의심"),
]

_FORCE_SUBMIT_PATTERNS = re.compile(
    r"(바로\s*제출|확인\s*없이|그냥\s*접수|즉시\s*신청|바로\s*신청|바로\s*접수)"
)


class SafetyResult(BaseModel):
    block: bool
    block_reason: str | None
    block_submit: bool
    required_hitl: bool
    sensitive_type: str | None = None


class SafetyAuditAgent(BaseAgent):
    def __init__(self):
        super().__init__(SAFETY_PROMPT)

    def run(self, user_message: str, planned_actions: list[str] | None = None) -> dict:
        planned_actions = planned_actions or []

        # 1단계: 정규식 사전 필터 (Gemini 호출 전)
        for pattern, label in _PII_PATTERNS:
            if pattern.search(user_message):
                audit = AuditEvent(
                    event_type="safety_block",
                    summary=f"민감정보 감지됨: {label}",
                )
                return SafetyResult(
                    block=True,
                    block_reason=f"{label}이(가) 감지되었습니다. 민감정보는 채팅에 입력하지 마세요.",
                    block_submit=False,
                    required_hitl=False,
                    sensitive_type=label,
                ).model_dump() | {"audit_event": audit.model_dump()}

        # 2단계: 강제 제출 요구 감지
        if _FORCE_SUBMIT_PATTERNS.search(user_message):
            audit = AuditEvent(
                event_type="hitl_gate",
                summary="사용자가 확인 없이 즉시 제출을 요청함 → HITL 강제",
            )
            return SafetyResult(
                block=False,
                block_reason=None,
                block_submit=True,
                required_hitl=True,
            ).model_dump() | {"audit_event": audit.model_dump()}

        # 정규식 통과 시 Gemini 호출 스킵 (Rate Limit 절약)
        audit = AuditEvent(
            event_type="state_update",
            summary="안전 검사 통과 (정규식 필터)",
        )
        return SafetyResult(
            block=False,
            block_reason=None,
            block_submit=False,
            required_hitl=False,
        ).model_dump() | {"audit_event": audit.model_dump()}
