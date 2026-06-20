from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_role
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.notification import (
    UserNotificationsListResponse,
    MarkReadRequest,
    BroadcastRequest,
)
from app.services.notification_service import (
    get_user_notifications,
    mark_as_read,
    mark_all_as_read,
    broadcast_to_all_employees,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=UserNotificationsListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_user_notifications(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
    )

@router.patch("/read", status_code=status.HTTP_200_OK)
async def mark_read(
    payload: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.notification_id:
        notif = await mark_as_read(
            db=db,
            notification_id=payload.notification_id,
            user_id=current_user.id,
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
    else:
        await mark_all_as_read(db=db, user_id=current_user.id)
    return {"message": "Notifications marked as read"}

@router.post("/broadcast", status_code=status.HTTP_201_CREATED)
async def broadcast(
    payload: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN")),
):
    await broadcast_to_all_employees(
        db=db,
        type=payload.type,
        title=payload.title,
        message=payload.message,
    )
    return {"message": "Notification broadcasted successfully"}
