import json
from pydantic import BaseModel
from .base import BaseAgent
from ..prompts import INTERVIEW_PROMPT
from ..schemas.profile import MoveProfile
from ..schemas.api_models import NextQuestion


class InterviewAgent(BaseAgent):
    def __init__(self):
        super().__init__(INTERVIEW_PROMPT)

    def run(self, move_profile: MoveProfile, intent: str) -> list[dict]:
        if move_profile.is_sufficient():
            return []

        user_content = (
            f"intent: {intent}\n"
            f"move_profile: {json.dumps(move_profile.model_dump(), ensure_ascii=False)}"
        )

        class QuestionList(BaseModel):
            questions: list[NextQuestion]

        result = self._call(user_content, QuestionList, temperature=0.3)
        questions = result.get("questions", [])
        return questions[:3]
