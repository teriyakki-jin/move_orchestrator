from typing import Literal
from pydantic import BaseModel


class TaskNode(BaseModel):
    task_id: str
    title: str
    priority: Literal["P0", "P1", "P2"]
    mandatory: bool = False
    route: Literal["gov24", "local_gov", "sinmungo", "offline"]
    risk_level: Literal["low", "medium", "high"] = "medium"
    requires_hitl: bool = False
    trigger_conditions: list[str] = []
    required_inputs: list[str] = []
    outputs: list[str] = []
    depends_on: list[str] = []
