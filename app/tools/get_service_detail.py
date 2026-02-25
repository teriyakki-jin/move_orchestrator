from ..db.services_db import SERVICES_DB


def get_service_detail(service_id: str) -> dict:
    """서비스 ID로 상세 정보를 조회합니다."""
    if service_id not in SERVICES_DB:
        return {"error": f"서비스를 찾을 수 없습니다: {service_id}"}
    return SERVICES_DB[service_id]
