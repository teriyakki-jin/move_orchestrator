from pydantic import BaseModel


class MissingField(BaseModel):
    field: str
    question: str
    options: list[str] = []


class FormFillResult(BaseModel):
    draft_payload: dict
    missing_fields: list[MissingField] = []
    warnings: list[str] = []
