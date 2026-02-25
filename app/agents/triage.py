from typing import Literal
from pydantic import BaseModel
from .base import BaseAgent
from ..prompts import TRIAGE_PROMPT


class TriageResult(BaseModel):
    intent: Literal["move", "move_plan", "other"]
    confidence: float
    sensitive: bool
    notes: str


class TriageAgent(BaseAgent):
    def __init__(self):
        super().__init__(TRIAGE_PROMPT)

    def run(self, user_message: str) -> dict:
        result = self._call(user_message, TriageResult, temperature=0.1)
        if not result:
            return TriageResult(
                intent="other", confidence=0.0, sensitive=False, notes="분류 실패"
            ).model_dump()
        return result
