from ..db.form_schemas_db import FORM_SCHEMAS


def get_form_schema(service_id: str) -> dict:
    """서비스의 신청서 필드 스키마를 조회합니다."""
    if service_id not in FORM_SCHEMAS:
        return {"error": f"신청서 스키마를 찾을 수 없습니다: {service_id}", "fields": []}
    return FORM_SCHEMAS[service_id]
