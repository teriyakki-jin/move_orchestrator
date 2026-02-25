import json
from pydantic import BaseModel
from .base import BaseAgent
from ..prompts import EVIDENCE_PROMPT
from ..schemas.profile import MoveProfile
from ..schemas.service import ServiceCard


class EvidenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(EVIDENCE_PROMPT)

    def run(
        self,
        task_graph: list[dict],
        move_profile: MoveProfile,
        db_results: list[dict],
    ) -> list[dict]:
        user_content = (
            f"task_graph: {json.dumps(task_graph, ensure_ascii=False)}\n"
            f"move_profile: {json.dumps(move_profile.model_dump(), ensure_ascii=False)}\n"
            f"db_results: {json.dumps(db_results, ensure_ascii=False)}"
        )

        class CardList(BaseModel):
            service_cards: list[ServiceCard]

        result = self._call(user_content, CardList, temperature=0.2)
        return result.get("service_cards", [])
