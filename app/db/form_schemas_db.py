"""신청서 필드 스키마 Mock 데이터베이스"""

FORM_SCHEMAS: dict[str, dict] = {
    "SVC001": {
        "service_id": "SVC001",
        "service_name": "전입신고",
        "fields": [
            {"name": "move_date", "label": "이사 날짜", "type": "date", "required": True, "is_sensitive": False},
            {"name": "new_address_sido", "label": "새 주소 시/도", "type": "string", "required": True, "is_sensitive": False},
            {"name": "new_address_sgg", "label": "새 주소 시/군/구", "type": "string", "required": True, "is_sensitive": False},
            {"name": "new_address_detail", "label": "새 주소 상세 (동/호수)", "type": "string", "required": True, "is_sensitive": True},
            {"name": "resident_number", "label": "주민등록번호", "type": "string", "required": True, "is_sensitive": True},
            {"name": "household_type", "label": "세대 유형", "type": "select", "required": True, "is_sensitive": False,
             "options": ["단독세대", "가족세대", "세대합가"]},
            {"name": "is_rental", "label": "거주 형태", "type": "select", "required": False, "is_sensitive": False,
             "options": ["전세", "월세", "자가"]},
        ]
    },
    "SVC003": {
        "service_id": "SVC003",
        "service_name": "차량 주소 변경",
        "fields": [
            {"name": "car_number", "label": "차량 번호", "type": "string", "required": True, "is_sensitive": False},
            {"name": "owner_name", "label": "소유자 이름", "type": "string", "required": True, "is_sensitive": False},
            {"name": "new_address_sido", "label": "새 주소 시/도", "type": "string", "required": True, "is_sensitive": False},
            {"name": "new_address_sgg", "label": "새 주소 시/군/구", "type": "string", "required": True, "is_sensitive": False},
            {"name": "new_address_detail", "label": "새 주소 상세", "type": "string", "required": True, "is_sensitive": True},
            {"name": "resident_number", "label": "주민등록번호", "type": "string", "required": True, "is_sensitive": True},
        ]
    },
}
