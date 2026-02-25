import uuid
from fastapi import APIRouter, HTTPException
from ..schemas.api_models import ChatRequest, ChatResponse, NextQuestion, SuggestedAction
from ..schemas.audit import AuditEvent
from ..schemas.task import TaskNode
from ..schemas.service import ServiceCard
from ..tools.create_draft import create_application_draft

router = APIRouter()
_turn_store: dict[str, int] = {}


def _get_turn(session_id: str) -> int:
    return _turn_store.get(session_id, 0)


@router.post("/chat-mock", response_model=ChatResponse)
def chat_mock(request: ChatRequest) -> ChatResponse:
    if not request.user_message.strip():
        raise HTTPException(status_code=400, detail="메시지를 입력해 주세요.")

    session_id = request.session_id.strip() or str(uuid.uuid4())
    turn = _get_turn(session_id) + 1
    _turn_store[session_id] = turn
    message = request.user_message

    if turn == 1:
        return ChatResponse(
            session_id=session_id,
            assistant_message_markdown="이사 도와드릴게요. 아래 질문에 답해 주세요.",
            next_questions=[
                NextQuestion(
                    id="move_date",
                    question="언제 이사하셨나요?",
                    why="전입신고 기한 계산에 필요합니다.",
                    options=["오늘", "어제", "직접 입력"],
                    optional=False,
                ),
                NextQuestion(
                    id="to_region",
                    question="어느 지역으로 이사하셨나요?",
                    why="관할 행정기관/서비스 추천에 필요합니다.",
                    options=["서울", "경기", "부산", "직접 입력"],
                    optional=False,
                ),
                NextQuestion(
                    id="household_type",
                    question="혼자 이사인가요, 가족 이사인가요?",
                    why="필수 제출 정보가 달라집니다.",
                    options=["혼자", "가족"],
                    optional=False,
                ),
            ],
            suggested_actions=[SuggestedAction(type="skip", label="건너뛰기", payload={})],
            audit_events=[AuditEvent(event_type="state_update", summary="mock interview turn")],
        )

    tasks = [
        TaskNode(
            task_id="TASK-001",
            title="전입신고",
            priority="P0",
            mandatory=True,
            route="gov24",
            risk_level="high",
            requires_hitl=True,
        ),
        TaskNode(
            task_id="TASK-002",
            title="도시가스 사용신청",
            priority="P1",
            mandatory=False,
            route="local_gov",
            risk_level="medium",
        ),
    ]
    cards = [
        ServiceCard(
            service_id="SVC001",
            service_name="전입신고",
            route="gov24",
            why_recommended=["이사 후 필수 신고입니다."],
            eligibility_summary="전입 세대주 또는 세대원",
            required_documents=["신분증"],
            application_channel=["온라인", "방문"],
            main_url="https://www.gov.kr",
            legal_basis=["주민등록법"],
            contact="정부24/주민센터",
        )
    ]

    wants_draft = any(k in message for k in ["초안", "신청서", "전입신고", "작성", "만들어"])
    if wants_draft or turn >= 3:
        draft = create_application_draft(
            service_id="SVC001",
            draft_payload={
                "move_date": "2026-02-25",
                "new_address_sido": "서울특별시",
                "new_address_sgg": "강남구",
                "new_address_detail": None,
                "resident_number": None,
                "household_type": "family",
                "is_rental": None,
            },
        )
        return ChatResponse(
            session_id=session_id,
            assistant_message_markdown=(
                "전입신고 초안을 만들었습니다.\n\n"
                f"- draft_id: `{draft['draft_id']}`\n"
                "- 제출 전 확인 버튼을 눌러 주세요."
            ),
            service_cards=cards,
            task_graph=tasks,
            suggested_actions=[
                SuggestedAction(
                    type="create_draft",
                    label="제출 확인",
                    payload={"draft_id": draft["draft_id"]},
                )
            ],
            hitl_required=True,
            draft_id=draft["draft_id"],
            audit_events=[AuditEvent(event_type="hitl_gate", summary="mock draft created")],
        )

    return ChatResponse(
        session_id=session_id,
        assistant_message_markdown="입력 확인했습니다. 우선순위 체크리스트와 추천 서비스를 안내합니다.",
        service_cards=cards,
        task_graph=tasks,
        suggested_actions=[
            SuggestedAction(type="create_draft", label="전입신고 초안 만들기", payload={"service_id": "SVC001"})
        ],
        audit_events=[AuditEvent(event_type="recommendation", summary="mock tasks/cards generated")],
    )
