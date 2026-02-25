from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from ..tools.create_draft import _draft_store

router = APIRouter()


class SubmitRequest(BaseModel):
    session_id: str
    confirmed: bool


@router.post("/submit/{draft_id}")
def submit_draft(draft_id: str, request: SubmitRequest) -> dict:
    draft = _draft_store.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="초안을 찾을 수 없습니다")

    if draft.get("status") == "submitted":
        raise HTTPException(status_code=409, detail="이미 제출된 초안입니다")

    if not request.confirmed:
        draft["status"] = "cancelled"
        draft["session_id"] = request.session_id
        draft["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        return {
            "draft_id": draft_id,
            "status": "cancelled",
            "submitted_at": None,
            "message": "초안이 취소되었습니다. 수정할 내용을 채팅으로 알려주세요.",
        }

    draft["status"] = "submitted"
    draft["session_id"] = request.session_id
    draft["submitted_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "draft_id": draft_id,
        "status": "submitted",
        "submitted_at": draft["submitted_at"],
        "message": "전입신고 초안이 제출 대기 상태로 등록되었습니다.",
    }
