import json
from ..agents import (
    SafetyAuditAgent, TriageAgent, InterviewAgent,
    DecompositionAgent, EvidenceAgent, FormFillAgent,
)
from ..tools.registry import dispatch
from ..schemas.api_models import ChatResponse, NextQuestion, SuggestedAction
from ..schemas.profile import MoveProfile
from ..schemas.task import TaskNode
from ..schemas.service import ServiceCard, EvidenceRef
from ..schemas.audit import AuditEvent
from ..core.config import get_settings
from ..core import mock_data
from .session import SessionStore, SessionData

# 에이전트 싱글턴 (앱 시작 시 1회 초기화)
_safety = SafetyAuditAgent()
_triage = TriageAgent()
_interview = InterviewAgent()
_decomposition = DecompositionAgent()
_evidence = EvidenceAgent()
_form_fill = FormFillAgent()


class Orchestrator:
    def __init__(self):
        self.session_store = SessionStore()

    def handle_turn(self, session_id: str, user_message: str) -> ChatResponse:
        audit_events: list[AuditEvent] = []

        # ── 1. Safety 검사 ──────────────────────────────────────────
        safety_result = _safety.run(user_message=user_message)
        if safety_result.get("audit_event"):
            audit_events.append(AuditEvent(**safety_result["audit_event"]))

        if safety_result.get("block"):
            return ChatResponse(
                session_id=session_id,
                assistant_message_markdown=(
                    f"⚠️ **입력이 차단되었습니다.**\n\n"
                    f"{safety_result.get('block_reason', '민감정보가 감지되었습니다.')}\n\n"
                    "주민등록번호, 계좌번호 등의 민감정보는 채팅에 입력하지 마세요."
                ),
                audit_events=audit_events,
            )

        # ── 3. 세션 로드 ────────────────────────────────────────────
        session: SessionData = self.session_store.get_or_create(session_id)
        session_id = session.session_id  # 새로 생성된 경우 UUID로 갱신

        # ── 2. Triage (기존 세션이면 스킵) ──────────────────────────
        _mock = get_settings().mock_mode
        if session.turn_count > 0:
            intent = "move"
        else:
            triage = mock_data.TRIAGE if _mock else _triage.run(user_message=user_message)
            intent = triage.get("intent", "other")
            if intent == "other":
                return ChatResponse(
                    session_id=session_id,
                    assistant_message_markdown=(
                        "안녕하세요! 저는 이사 관련 민원을 도와드리는 AI입니다. 😊\n\n"
                        "이사하셨거나 이사 예정이신가요? 이사 관련 질문을 해 주세요!\n\n"
                        "예시: \"이사했는데 뭐부터 해야 해?\", \"다음 달에 이사하는데 준비할 게 뭐야?\""
                    ),
                    audit_events=audit_events,
                )

        session.turn_count += 1

        # HITL 강제 (제출 요청 감지)
        hitl_required = safety_result.get("block_submit", False)

        # ── 4. 메시지에서 프로필 먼저 업데이트 (인터뷰 전에) ─────────
        session = self._update_profile_from_message(session, user_message)

        # ── 5. Interview (프로필 미수집 시) ─────────────────────────
        # mock 모드: 2턴부터 프로필 강제 채움
        if _mock and session.turn_count >= 2 and not session.move_profile.is_sufficient():
            from datetime import date, timedelta
            session.move_profile = session.move_profile.merge_patch({
                "move_date": (date.today() - timedelta(days=1)).isoformat(),
                "to_region": {"sido": "서울특별시", "sgg": "강남구"},
                "household_type": "family",
            })

        # 코드 기반 인터뷰 — 빠진 필드만 질문 생성 (LLM 불필요)
        next_questions = self._build_interview_questions(session.move_profile)

        # 아직 프로필이 충분하지 않으면 질문만 반환
        if next_questions and not session.move_profile.is_sufficient():
            self.session_store.update(session_id, session)

            audit_events.append(AuditEvent(
                event_type="state_update",
                summary=f"인터뷰 진행 중 (턴 {session.turn_count})",
            ))

            return ChatResponse(
                session_id=session_id,
                assistant_message_markdown=self._build_interview_message(
                    next_questions, session.move_profile
                ),
                next_questions=next_questions,
                suggested_actions=[
                    SuggestedAction(type="skip", label="건너뛰기", payload={})
                ],
                audit_events=audit_events,
            )

        # ── 5. Decomposition ────────────────────────────────────────
        if not session.task_graph:
            tasks_raw = mock_data.DECOMPOSITION if _mock else _decomposition.run(move_profile=session.move_profile)
            session.task_graph = [
                TaskNode(**t) if isinstance(t, dict) else t for t in tasks_raw
            ]
            audit_events.append(AuditEvent(
                event_type="recommendation",
                summary=f"태스크 {len(session.task_graph)}개 생성",
            ))

        # ── 6. 서비스 검색 (Mock DB) ────────────────────────────────
        tags = ["이사"]
        if session.move_profile.has_children == "yes":
            tags.append("자녀")
        if session.move_profile.vehicles.car == "yes":
            tags.append("차량")

        db_results = dispatch(
            "search_services",
            query="이사",
            region=session.move_profile.to_region.sido,
            tags=tags,
        )

        # ── 7. Evidence (서비스 카드 생성) ──────────────────────────
        if not session.service_cards:
            cards_raw = mock_data.EVIDENCE if _mock else _evidence.run(
                task_graph=[t.model_dump() for t in session.task_graph],
                move_profile=session.move_profile,
                db_results=db_results,
            )
            session.service_cards = [
                ServiceCard(**c) if isinstance(c, dict) else c for c in cards_raw
            ]
            audit_events.append(AuditEvent(
                event_type="recommendation",
                summary=f"서비스 카드 {len(session.service_cards)}개 생성",
                evidence_refs=[c.service_id if hasattr(c, 'service_id') else c.get('service_id', '') for c in session.service_cards],
            ))

        # ── 8. Form-Fill (초안 요청 감지) ───────────────────────────
        form_result = None
        draft_result = None
        if self._wants_draft(user_message):
            schema = dispatch("get_form_schema", service_id="SVC001")
            form_result = mock_data.FORM_FILL if _mock else _form_fill.run(
                service_id="SVC001",
                move_profile=session.move_profile,
                form_schema=schema,
            )
            if form_result:
                draft_payload = form_result.get("draft_payload", {})
                draft_result = dispatch(
                    "create_application_draft",
                    service_id="SVC001",
                    draft_payload=draft_payload,
                )
                hitl_required = True
                audit_events.append(AuditEvent(
                    event_type="hitl_gate",
                    summary=f"전입신고 초안 생성 완료 (draft_id: {draft_result.get('draft_id')})",
                    tool_name="create_application_draft",
                ))

        # ── 9. 세션 저장 ────────────────────────────────────────────
        session.audit_log.extend(audit_events)
        self.session_store.update(session_id, session)

        # ── 10. 응답 조립 ────────────────────────────────────────────
        suggested_actions = self._build_actions(session, draft_result)
        markdown = self._build_response_markdown(session, form_result, draft_result, hitl_required)

        return ChatResponse(
            session_id=session_id,
            assistant_message_markdown=markdown,
            next_questions=next_questions,
            suggested_actions=suggested_actions,
            service_cards=session.service_cards,
            task_graph=session.task_graph,
            audit_events=audit_events,
            hitl_required=hitl_required,
            draft_id=draft_result.get("draft_id") if draft_result else None,
            draft_preview=draft_result.get("preview") if draft_result else None,
        )

    def _update_profile_from_message(self, session: SessionData, message: str) -> SessionData:
        """간단한 키워드 기반 프로필 업데이트 (Gemini 없이)"""
        from datetime import date, timedelta
        profile = session.move_profile
        patch = {}

        # 날짜 감지
        if profile.move_date == "unknown":
            today = date.today()
            if "오늘" in message:
                patch["move_date"] = today.isoformat()
            elif "어제" in message:
                patch["move_date"] = (today - timedelta(days=1)).isoformat()
            elif "그제" in message or "그저께" in message:
                patch["move_date"] = (today - timedelta(days=2)).isoformat()
            else:
                import re
                m = re.search(r"(\d{4})[년\-/]?\s*(\d{1,2})[월\-/]?\s*(\d{1,2})일?", message)
                if m:
                    patch["move_date"] = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                else:
                    m2 = re.search(r"(\d{1,2})[월\-/]\s*(\d{1,2})일?", message)
                    if m2:
                        patch["move_date"] = f"{today.year}-{int(m2.group(1)):02d}-{int(m2.group(2)):02d}"

        import re

        def _particle(msg: str, keyword: str) -> str:
            """키워드 바로 뒤 조사를 반환: 'from'(에서) | 'to'(로/으로) | 'unknown'"""
            idx = msg.find(keyword)
            if idx == -1:
                return "unknown"
            after = msg[idx + len(keyword):]
            # '경기도로'처럼 지명 접미사(도/시/군/구)가 붙은 경우 한 글자 건너뜀
            if after and after[0] in "도시군구":
                after = after[1:]
            if after.startswith("에서"):
                return "from"
            if after.startswith("으로") or after.startswith("로"):
                return "to"
            if after.startswith("에") and not after.startswith("에서"):
                return "to"
            if not after or after[0] in (" ", ",", ".", "!"):
                return "to"
            return "unknown"

        # 시/도 감지
        sido_keywords = {
            "서울": "서울특별시", "부산": "부산광역시", "인천": "인천광역시",
            "대구": "대구광역시", "광주": "광주광역시", "대전": "대전광역시",
            "울산": "울산광역시", "세종": "세종특별자치시", "경기": "경기도",
            "강원": "강원도", "충북": "충청북도", "충남": "충청남도",
            "전북": "전라북도", "전남": "전라남도", "경북": "경상북도",
            "경남": "경상남도", "제주": "제주특별자치도",
        }
        detected_sido = None
        if profile.to_region.sido == "unknown":
            # 1차: 명확히 목적지(로/으로)인 키워드 우선
            for keyword, sido in sido_keywords.items():
                if keyword in message and _particle(message, keyword) == "to":
                    detected_sido = sido
                    patch["to_region"] = {"sido": sido, "sgg": profile.to_region.sgg}
                    break
            # 2차: 조사 불분명한 경우 fallback (에서가 아닌 것만)
            if not detected_sido:
                for keyword, sido in sido_keywords.items():
                    if keyword in message and _particle(message, keyword) != "from":
                        detected_sido = sido
                        patch["to_region"] = {"sido": sido, "sgg": profile.to_region.sgg}
                        break

        # 구/군/시 감지 (sgg) — (sgg명, sido명) 튜플로 sido 자동 추론 포함
        sgg_keywords = {
            # 서울 25개 구
            "강남구": ("강남구", "서울특별시"), "강동구": ("강동구", "서울특별시"),
            "강북구": ("강북구", "서울특별시"), "강서구": ("강서구", "서울특별시"),
            "관악구": ("관악구", "서울특별시"), "광진구": ("광진구", "서울특별시"),
            "구로구": ("구로구", "서울특별시"), "금천구": ("금천구", "서울특별시"),
            "노원구": ("노원구", "서울특별시"), "도봉구": ("도봉구", "서울특별시"),
            "동대문구": ("동대문구", "서울특별시"), "동작구": ("동작구", "서울특별시"),
            "마포구": ("마포구", "서울특별시"), "서대문구": ("서대문구", "서울특별시"),
            "서초구": ("서초구", "서울특별시"), "성동구": ("성동구", "서울특별시"),
            "성북구": ("성북구", "서울특별시"), "송파구": ("송파구", "서울특별시"),
            "양천구": ("양천구", "서울특별시"), "영등포구": ("영등포구", "서울특별시"),
            "용산구": ("용산구", "서울특별시"), "은평구": ("은평구", "서울특별시"),
            "종로구": ("종로구", "서울특별시"), "중구": ("중구", "서울특별시"),
            "중랑구": ("중랑구", "서울특별시"),
            # 부산 주요 구
            "해운대구": ("해운대구", "부산광역시"), "부산진구": ("부산진구", "부산광역시"),
            "동래구": ("동래구", "부산광역시"), "남구": ("남구", "부산광역시"),
            "북구": ("북구", "부산광역시"), "사하구": ("사하구", "부산광역시"),
            "금정구": ("금정구", "부산광역시"), "연제구": ("연제구", "부산광역시"),
            "수영구": ("수영구", "부산광역시"), "사상구": ("사상구", "부산광역시"),
            "기장군": ("기장군", "부산광역시"),
            # 인천 주요 구
            "미추홀구": ("미추홀구", "인천광역시"), "연수구": ("연수구", "인천광역시"),
            "남동구": ("남동구", "인천광역시"), "부평구": ("부평구", "인천광역시"),
            "계양구": ("계양구", "인천광역시"), "강화군": ("강화군", "인천광역시"),
            "옹진군": ("옹진군", "인천광역시"),
            # 대구 주요 구
            "달서구": ("달서구", "대구광역시"), "달성군": ("달성군", "대구광역시"),
            "수성구": ("수성구", "대구광역시"),
            # 경기 주요 시/군
            "수원시": ("수원시", "경기도"), "성남시": ("성남시", "경기도"),
            "용인시": ("용인시", "경기도"), "부천시": ("부천시", "경기도"),
            "안산시": ("안산시", "경기도"), "안양시": ("안양시", "경기도"),
            "남양주시": ("남양주시", "경기도"), "화성시": ("화성시", "경기도"),
            "평택시": ("평택시", "경기도"), "의정부시": ("의정부시", "경기도"),
            "시흥시": ("시흥시", "경기도"), "파주시": ("파주시", "경기도"),
            "광명시": ("광명시", "경기도"), "김포시": ("김포시", "경기도"),
            "군포시": ("군포시", "경기도"), "하남시": ("하남시", "경기도"),
            "오산시": ("오산시", "경기도"), "이천시": ("이천시", "경기도"),
            "안성시": ("안성시", "경기도"), "구리시": ("구리시", "경기도"),
            "의왕시": ("의왕시", "경기도"), "양주시": ("양주시", "경기도"),
            "포천시": ("포천시", "경기도"), "고양시": ("고양시", "경기도"),
            "광주시": ("광주시", "경기도"),
            # 경기 유명 지역명 (시 이름 없이 쓰는 경우)
            "판교": ("성남시", "경기도"), "분당": ("성남시", "경기도"),
            "일산": ("고양시", "경기도"), "동탄": ("화성시", "경기도"),
            "수지": ("용인시", "경기도"), "광교": ("수원시", "경기도"),
            "검단": ("인천광역시", "인천광역시"),
            # 충청/전라/경상 주요 시
            "청주시": ("청주시", "충청북도"), "천안시": ("천안시", "충청남도"),
            "전주시": ("전주시", "전라북도"), "창원시": ("창원시", "경상남도"),
            "진주시": ("진주시", "경상남도"), "포항시": ("포항시", "경상북도"),
            "경주시": ("경주시", "경상북도"),
        }
        if profile.to_region.sgg in ("unknown", None):
            current_sido = detected_sido or profile.to_region.sido

            def _apply_sgg(keyword: str):
                sgg_val, inferred_sido = sgg_keywords[keyword]
                patch.setdefault("to_region", {"sido": current_sido, "sgg": "unknown"})
                patch["to_region"]["sgg"] = sgg_val
                # sido가 아직 unknown이면 sgg로부터 추론
                if patch["to_region"].get("sido") in ("unknown", None) and inferred_sido:
                    patch["to_region"]["sido"] = inferred_sido

            # 1차: 명확히 목적지(로/으로)인 sgg 우선
            for keyword in sgg_keywords:
                if keyword in message and _particle(message, keyword) == "to":
                    _apply_sgg(keyword)
                    break
            # 2차: 조사 불분명하되 에서가 아닌 것
            if "to_region" not in patch or patch["to_region"].get("sgg") == "unknown":
                for keyword in sgg_keywords:
                    if keyword in message and _particle(message, keyword) != "from":
                        _apply_sgg(keyword)
                        break

        # 세대 유형 감지
        if profile.household_type == "unknown":
            if any(k in message for k in ["혼자", "1인", "싱글", "나 혼자", "1인 가구"]):
                patch["household_type"] = "single"
            elif any(k in message for k in ["신혼", "신혼부부", "부부"]):
                patch["household_type"] = "family"
            elif any(k in message for k in ["가족", "세대", "아내", "남편", "아이", "자녀", "자녀 있는", "4인", "3인", "5인"]):
                patch["household_type"] = "family"
            elif "기타" in message:
                patch["household_type"] = "single"

        # 자녀 유무 감지
        if profile.has_children == "unknown":
            if any(k in message for k in ["아이", "자녀", "아들", "딸", "초등", "학교"]):
                patch["has_children"] = "yes"

        # 차량 유무 감지
        if profile.vehicles.car == "unknown":
            if any(k in message for k in ["차", "자동차", "차량"]):
                patch["vehicles"] = {"car": "yes"}

        if patch:
            session.move_profile = profile.merge_patch(patch)
        return session

    def _build_interview_questions(self, profile: MoveProfile) -> list[NextQuestion]:
        """빠진 필드만 코드로 직접 생성 — LLM 호출 없음"""
        questions = []

        if profile.move_date == "unknown":
            questions.append(NextQuestion(
                id="move_date",
                question="이사 날짜가 언제인가요?",
                why="신고 기한(전입신고는 이사 후 14일 이내)을 계산합니다.",
                options=["오늘", "어제", "그저께", "이번 주"],
                optional=False,
            ))

        if profile.to_region.sido == "unknown":
            questions.append(NextQuestion(
                id="to_region.sido",
                question="어느 시/도로 이사하셨나요?",
                why="이사 목적지에 맞는 서비스를 안내해 드립니다.",
                options=["서울특별시", "경기도", "부산광역시", "인천광역시",
                         "대구광역시", "광주광역시", "대전광역시", "울산광역시",
                         "세종특별자치시", "강원도", "충청북도", "충청남도",
                         "전라북도", "전라남도", "경상북도", "경상남도", "제주특별자치도"],
                optional=False,
            ))

        if profile.household_type == "unknown":
            questions.append(NextQuestion(
                id="household_type",
                question="어떤 유형의 가구이신가요?",
                why="가구 유형에 따라 필요한 행정 서비스가 달라집니다.",
                options=["1인 가구", "신혼부부", "자녀 있는 가족", "기타"],
                optional=False,
            ))

        return questions

    def _wants_draft(self, message: str) -> bool:
        keywords = ["초안", "신청서", "전입신고", "만들어", "작성", "신청"]
        return any(k in message for k in keywords)

    def _build_interview_message(self, questions: list, profile: MoveProfile) -> str:
        lines = ["이사 관련 민원을 도와드릴게요!\n"]

        # 이미 파악된 정보 표시
        confirmed = []
        if profile.move_date != "unknown":
            confirmed.append(f"- **이사 날짜**: {profile.move_date} ✓")
        region = ""
        if profile.to_region.sido != "unknown":
            region = profile.to_region.sido
            if profile.to_region.sgg not in ("unknown", None):
                region += f" {profile.to_region.sgg}"
            confirmed.append(f"- **이사 지역**: {region} ✓")
        if profile.household_type != "unknown":
            confirmed.append(f"- **세대 유형**: {profile.household_type} ✓")

        if confirmed:
            lines.append("**확인된 정보:**")
            lines.extend(confirmed)
            lines.append("")

        lines.append("**추가로 필요한 정보:**")
        for q in questions:
            q_dict = q if isinstance(q, dict) else q.model_dump()
            lines.append(f"- {q_dict['question']}")

        return "\n".join(lines)

    def _build_response_markdown(
        self, session: SessionData, form_result, draft_result, hitl_required: bool
    ) -> str:
        profile = session.move_profile
        lines = []

        # 요약
        lines.append(f"## 이사 민원 안내")
        lines.append(f"**이사 지역**: {profile.to_region.sido} {profile.to_region.sgg}  ")
        lines.append(f"**이사 날짜**: {profile.move_date}  ")
        lines.append(f"**세대 유형**: {profile.household_type}\n")

        # 체크리스트
        if session.task_graph:
            lines.append("### ✅ 해야 할 일 (우선순위)")
            for task in session.task_graph:
                t = task if isinstance(task, dict) else task.model_dump()
                emoji = "🔴" if t["priority"] == "P0" else ("🟡" if t["priority"] == "P1" else "🟢")
                hitl = " *(최종 확인 필요)*" if t.get("requires_hitl") else ""
                lines.append(f"- {emoji} **{t['title']}** ({t['priority']}){hitl}")
            lines.append("")

        # 서비스 카드 요약
        if session.service_cards:
            lines.append("### 📋 추천 서비스")
            for card in session.service_cards[:3]:
                c = card if isinstance(card, dict) else card.model_dump()
                lines.append(f"\n**{c['service_name']}**")
                if c.get("why_recommended"):
                    lines.append(f"- 추천 이유: {c['why_recommended'][0]}")
                if c.get("main_url"):
                    lines.append(f"- 링크: {c['main_url']}")
                if c.get("required_documents"):
                    lines.append(f"- 필요 서류: {', '.join(c['required_documents'])}")
            lines.append("")

        # 초안 결과
        if draft_result:
            lines.append("### 📝 전입신고 초안")
            lines.append(f"**초안 ID**: `{draft_result['draft_id']}`\n")
            lines.append("```")
            for k, v in draft_result.get("preview", {}).items():
                lines.append(f"{k}: {v}")
            lines.append("```")
            lines.append("")

        # 안전 안내
        lines.append("---")
        lines.append("⚠️ **주의**: 민감정보(주민번호, 상세주소)는 채팅에 입력하지 마세요.")
        if hitl_required:
            lines.append("📌 **제출 전 반드시 내용을 직접 확인하신 후 진행해 주세요.**")

        return "\n".join(lines)

    def _build_actions(self, session: SessionData, draft_result) -> list[SuggestedAction]:
        actions = []
        if not self._wants_draft(""):
            actions.append(SuggestedAction(
                type="create_draft",
                label="전입신고 초안 만들기",
                payload={"service_id": "SVC001"},
            ))
        if session.service_cards:
            first = session.service_cards[0]
            url = first.main_url if hasattr(first, 'main_url') else first.get('main_url', '')
            if url:
                actions.append(SuggestedAction(
                    type="open_link",
                    label="gov.kr 바로가기",
                    payload={"url": url},
                ))
        actions.append(SuggestedAction(
            type="call_center",
            label="주민센터 문의",
            payload={"contact": "가까운 읍·면·동 행정복지센터"},
        ))
        return actions
