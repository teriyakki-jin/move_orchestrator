import json
from pydantic import BaseModel
from .base import BaseAgent
from ..prompts import DECOMPOSITION_PROMPT
from ..schemas.profile import MoveProfile
from ..schemas.task import TaskNode


class DecompositionAgent(BaseAgent):
    def __init__(self):
        super().__init__(DECOMPOSITION_PROMPT)

    def run(self, move_profile: MoveProfile) -> list[dict]:
        user_content = f"move_profile: {json.dumps(move_profile.model_dump(), ensure_ascii=False)}"

        class TaskList(BaseModel):
            tasks: list[TaskNode]

        result = self._call(user_content, TaskList, temperature=0.1)
        return result.get("tasks", [])
