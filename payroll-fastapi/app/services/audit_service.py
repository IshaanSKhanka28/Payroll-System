import uuid
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User

async def log_action(
    db: AsyncSession,
    performed_by: uuid.UUID,
    action: str,
    entity: str,
    entity_id: str,
    changes: dict | None,
) -> None:
    audit_log = AuditLog(
        performed_by=performed_by,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        changes=changes,
    )
    db.add(audit_log)
    await db.commit()

class AuditLogger:
    def __init__(self, action: str, entity: str):
        self.action = action
        self.entity = entity

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        yield
        if hasattr(request.state, "audit_changes") and request.state.audit_changes:
            entity_id = getattr(request.state, "audit_entity_id", None)
            await log_action(
                db=db,
                performed_by=current_user.id,
                action=self.action,
                entity=self.entity,
                entity_id=str(entity_id) if entity_id else "",
                changes=request.state.audit_changes,
            )
