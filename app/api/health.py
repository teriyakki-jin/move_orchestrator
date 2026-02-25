from fastapi import APIRouter
from ..core.config import get_settings, _ENV_PATH

router = APIRouter()


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.openai_model,
        "env_path": str(_ENV_PATH),
        "env_exists": _ENV_PATH.exists(),
    }
