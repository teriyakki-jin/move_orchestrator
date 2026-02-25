import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from ..schemas.profile import MoveProfile
from ..schemas.task import TaskNode
from ..schemas.service import ServiceCard
from ..schemas.audit import AuditEvent
from .session_db import SQLiteSessionDB


class SessionData(BaseModel):
    session_id: str
    move_profile: MoveProfile = MoveProfile()
    task_graph: list[TaskNode] = []
    service_cards: list[ServiceCard] = []
    audit_log: list[AuditEvent] = []
    turn_count: int = 0
    created_at: str = ""
    last_active_at: str = ""

    def model_post_init(self, __context):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        self.last_active_at = now


class SessionStore:
    def __init__(self):
        self._db = SQLiteSessionDB()

    def get_or_create(self, session_id: str) -> SessionData:
        if not session_id:
            session_id = str(uuid.uuid4())
        existing = self.get(session_id)
        if existing:
            return existing
        created = SessionData(session_id=session_id)
        self.update(session_id, created)
        return created

    def update(self, session_id: str, data: SessionData) -> None:
        data.last_active_at = datetime.now(timezone.utc).isoformat()
        self._db.upsert(
            session_id=session_id,
            data_json=data.model_dump_json(),
            created_at=data.created_at,
            last_active_at=data.last_active_at,
        )

    def get(self, session_id: str) -> SessionData | None:
        row = self._db.get(session_id)
        if not row:
            return None
        return SessionData.model_validate_json(row["data"])
