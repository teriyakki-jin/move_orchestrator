import json
from .base import BaseAgent
from ..prompts import FORM_FILL_PROMPT
from ..schemas.profile import MoveProfile
from ..schemas.form import FormFillResult


class FormFillAgent(BaseAgent):
    def __init__(self):
        super().__init__(FORM_FILL_PROMPT)

    def run(
        self,
        service_id: str,
        move_profile: MoveProfile,
        form_schema: dict,
    ) -> dict:
        user_content = (
            f"service_id: {service_id}\n"
            f"move_profile: {json.dumps(move_profile.model_dump(), ensure_ascii=False)}\n"
            f"form_schema: {json.dumps(form_schema, ensure_ascii=False)}"
        )

        result = self._call(user_content, FormFillResult, temperature=0.1)
        if not result or not result.get("draft_payload"):
            # Gemini 실패 시 프로필에서 직접 채우는 폴백
            return self._fallback_fill(service_id, move_profile, form_schema)
        return result

    def _fallback_fill(self, service_id: str, move_profile, form_schema: dict) -> dict:
        """Gemini 실패 시 프로필 정보로 직접 신청서 채우기"""
        fields = form_schema.get("fields", [])
        draft_payload = {}
        missing_fields = []
        warnings = [
            "제출 전 반드시 내용을 확인하세요.",
            "민감정보(주민번호, 상세주소)는 안전한 입력 단계에서만 입력하세요.",
        ]

        profile_map = {
            "move_date": move_profile.move_date if move_profile.move_date != "unknown" else None,
            "new_address_sido": move_profile.to_region.sido if move_profile.to_region.sido != "unknown" else None,
            "new_address_sgg": move_profile.to_region.sgg if move_profile.to_region.sgg != "unknown" else None,
            "household_type": move_profile.household_type if move_profile.household_type != "unknown" else None,
            "is_rental": move_profile.is_rental if move_profile.is_rental != "unknown" else None,
        }

        for field in fields:
            name = field["name"]
            if field.get("is_sensitive"):
                draft_payload[name] = None
            elif name in profile_map and profile_map[name] is not None:
                draft_payload[name] = profile_map[name]
            else:
                draft_payload[name] = None
                if field.get("required"):
                    missing_fields.append({
                        "field": name,
                        "question": f"{field.get('label', name)}을(를) 입력해주세요.",
                        "options": field.get("options", []),
                    })

        return {
            "draft_payload": draft_payload,
            "missing_fields": missing_fields,
            "warnings": warnings,
        }
