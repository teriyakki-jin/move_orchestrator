from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    event_type: Literal["recommendation", "tool_call", "hitl_gate", "safety_block", "state_update"]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str
    evidence_refs: list[str] = []
    tool_name: str | None = None
    tool_args_redacted: bool = True
