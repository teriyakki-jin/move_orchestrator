import uuid
from datetime import datetime, timezone

_draft_store: dict[str, dict] = {}


def create_application_draft(service_id: str, draft_payload: dict) -> dict:
    """신청서 초안을 생성합니다. 실제 제출은 하지 않습니다 (HITL 게이트)."""
    draft_id = f"DRAFT-{str(uuid.uuid4())[:8].upper()}"

    # 민감 필드 마스킹
    sensitive_keys = {"resident_number", "new_address_detail"}
    preview = {}
    for k, v in draft_payload.items():
        if k in sensitive_keys:
            preview[k] = "****(안전한 입력 단계에서 입력 필요)"
        else:
            preview[k] = v

    missing = [k for k, v in draft_payload.items() if v is None]

    draft = {
        "draft_id": draft_id,
        "service_id": service_id,
        "preview": preview,
        "missing_fields": missing,
        "status": "draft",
        "note": "⚠️ 초안이 생성되었습니다. 실제 제출 전 반드시 내용을 확인해 주세요.",
        "submitted_at": None,
        "session_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _draft_store[draft_id] = draft
    return draft
