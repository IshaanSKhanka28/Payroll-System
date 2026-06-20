import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


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
