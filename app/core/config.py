from pathlib import Path
from pydantic_settings import BaseSettings

# 이 파일 기준으로 프로젝트 루트의 .env 절대 경로
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    openai_api_key: str = "mock"
    openai_model: str = "gpt-4o-mini"
    max_turns: int = 20
    profile_min_fields: int = 3
    mock_mode: bool = False  # True 시 LLM 호출 없이 목데이터 반환

    class Config:
        env_file = str(_ENV_PATH)
        env_file_encoding = "utf-8"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
