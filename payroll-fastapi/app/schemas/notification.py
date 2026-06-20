import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.notification import NotificationType

class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    is_read: bool
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserNotificationsListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int

class MarkReadRequest(BaseModel):
    notification_id: uuid.UUID | None = None

class BroadcastRequest(BaseModel):
    type: NotificationType
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
