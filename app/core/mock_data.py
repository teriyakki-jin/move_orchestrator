"""MOCK_MODE=true 일 때 각 에이전트가 반환할 고정 데이터"""
from datetime import date, timedelta

yesterday = (date.today() - timedelta(days=1)).isoformat()


TRIAGE = {"intent": "move", "confidence": 1.0, "sensitive": False, "notes": "mock"}

INTERVIEW = [
    {"id": "move_date", "question": "이사 날짜는 언제인가요?", "why": "필수 정보", "options": [], "optional": False},
    {"id": "to_region.sido", "question": "어느 시/도로 이사하셨나요?", "why": "필수 정보",
     "options": ["서울특별시", "경기도", "부산광역시"], "optional": False},
    {"id": "household_type", "question": "세대 구성은 어떻게 되시나요?", "why": "필수 정보",
     "options": ["1인 가구", "가족", "부부"], "optional": False},
]

DECOMPOSITION = [
    {
        "task_id": "task_001", "title": "전입신고", "priority": "P0", "mandatory": True,
        "route": "gov24", "risk_level": "high", "requires_hitl": True,
        "trigger_conditions": [], "required_inputs": ["move_date", "to_region.sido"],
        "outputs": ["전입신고_완료"], "depends_on": [],
    },
    {
        "task_id": "task_002", "title": "건강보험 주소 변경", "priority": "P0", "mandatory": True,
        "route": "gov24", "risk_level": "medium", "requires_hitl": False,
        "trigger_conditions": [], "required_inputs": ["to_region.sido"],
        "outputs": ["건강보험_주소_변경완료"], "depends_on": ["task_001"],
    },
]

EVIDENCE = [
    {
        "service_id": "SVC001", "service_name": "전입신고", "route": "gov24",
        "why_recommended": ["이사 후 14일 내 법정 의무 신고"],
        "eligibility_summary": "이사한 날로부터 14일 이내 신고",
        "required_documents": ["신분증"],
        "application_channel": ["online", "mobile", "visit"],
        "main_url": "https://www.gov.kr/portal/service/serviceInfo/PTR000050007",
        "legal_basis": ["주민등록법 제11조"], "contact": "읍·면·동 행정복지센터", "evidence": [],
    },
    {
        "service_id": "SVC002", "service_name": "건강보험 주소 변경", "route": "gov24",
        "why_recommended": ["주소 변경 후 보험료 산정에 영향"],
        "eligibility_summary": "전입신고 후 자동 연동 또는 별도 신청",
        "required_documents": ["신분증"],
        "application_channel": ["online", "phone"],
        "main_url": "https://www.nhis.or.kr", "legal_basis": [], "contact": "건강보험공단 1577-1000", "evidence": [],
    },
]

FORM_FILL = {
    "draft_payload": {
        "move_date": yesterday,
        "new_address_sido": "서울특별시",
        "new_address_sgg": "강남구",
        "new_address_detail": None,
        "resident_number": None,
        "household_type": "가족세대",
        "is_rental": None,
    },
    "missing_fields": [
        {"field": "new_address_detail", "question": "상세 주소를 입력해 주세요.", "options": []},
        {"field": "resident_number", "question": "주민등록번호를 입력해 주세요.", "options": []},
    ],
    "warnings": ["제출 전 반드시 내용을 확인하세요.", "민감정보는 안전한 입력 단계에서만 입력하세요."],
}
