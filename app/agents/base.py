from abc import ABC, abstractmethod
from ..core.openai_client import generate_structured


class BaseAgent(ABC):
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def _call(self, user_content: str, response_schema: type, temperature: float = 0.2) -> dict:
        return generate_structured(self.system_prompt, user_content, response_schema, temperature)

    @abstractmethod
    def run(self, **kwargs) -> dict:
        pass
