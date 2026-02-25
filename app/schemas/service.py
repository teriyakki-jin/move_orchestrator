from pydantic import BaseModel, model_validator


class EvidenceRef(BaseModel):
    type: str
    key: str
    value: str


class ServiceCard(BaseModel):
    service_id: str
    service_name: str
    route: str
    why_recommended: list[str] = []
    eligibility_summary: str = ""
    required_documents: list[str] = []
    application_channel: list[str] = []
    main_url: str = ""
    legal_basis: list[str] = []
    contact: str = ""
    evidence: list[EvidenceRef] = []

    @model_validator(mode="after")
    def check_evidence(self) -> "ServiceCard":
        if not self.evidence:
            # 자동으로 evidence 생성 (main_url or legal_basis 기반)
            if self.main_url:
                self.evidence = [EvidenceRef(type="db_field", key="main_url", value=self.main_url)]
            elif self.legal_basis:
                self.evidence = [EvidenceRef(type="db_field", key="legal_basis", value=self.legal_basis[0])]
        return self
