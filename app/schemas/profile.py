from typing import Literal
from pydantic import BaseModel


class Region(BaseModel):
    sido: str = "unknown"
    sgg: str = "unknown"


class Vehicles(BaseModel):
    car: Literal["unknown", "yes", "no"] = "unknown"
    motorcycle: Literal["unknown", "yes", "no"] = "unknown"
    pm: Literal["unknown", "yes", "no"] = "unknown"


class Needs(BaseModel):
    school_transfer: Literal["unknown", "yes", "no"] = "unknown"
    childcare: Literal["unknown", "yes", "no"] = "unknown"
    parking: Literal["unknown", "yes", "no"] = "unknown"
    waste_disposal: Literal["unknown", "yes", "no"] = "unknown"


class Consent(BaseModel):
    admin_info_query: bool = False
    notifications: bool = False


class RiskFlags(BaseModel):
    sensitive_info_detected: bool = False
    user_asking_to_submit_without_review: bool = False


class MoveProfile(BaseModel):
    move_date: str = "unknown"
    from_region: Region = Region()
    to_region: Region = Region()
    household_type: Literal["unknown", "single", "family"] = "unknown"
    is_rental: Literal["unknown", "rental", "owner"] = "unknown"
    has_children: Literal["unknown", "yes", "no"] = "unknown"
    vehicles: Vehicles = Vehicles()
    needs: Needs = Needs()
    consent: Consent = Consent()
    risk_flags: RiskFlags = RiskFlags()

    def is_sufficient(self) -> bool:
        """전입신고 등 기본 추천을 위한 최소 정보 수집 여부"""
        return (
            self.move_date != "unknown"
            and self.to_region.sido != "unknown"
            and self.household_type != "unknown"
        )

    def merge_patch(self, patch: dict) -> "MoveProfile":
        """state_patch를 현재 프로필에 병합"""
        current = self.model_dump()
        _deep_merge(current, patch)
        return MoveProfile.model_validate(current)


def _deep_merge(base: dict, patch: dict) -> None:
    for key, value in patch.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
