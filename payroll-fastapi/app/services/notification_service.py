import uuid
from sqlalchemy.future import select
from sqlalchemy import func, update
from app.models.notification import Notification, NotificationType
from app.models.employee import Employee, EmployeeStatus

def create_notification(session, user_id, type, title, message):
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message
    )
    session.add(notif)
    return notif

async def get_user_notifications(db, user_id, page, limit):
    query = select(Notification).where(Notification.user_id == user_id).order_by(Notification.sent_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    res = await db.execute(query)
    notifications = res.scalars().all()
    
    count_res = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == user_id, Notification.is_read == False)
    )
    unread_count = count_res.scalar() or 0
    return {
        "notifications": notifications,
        "unread_count": unread_count
    }

async def mark_as_read(db, notification_id, user_id):
    res = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    )
    notif = res.scalars().first()
    if notif:
        notif.is_read = True
        await db.commit()
        await db.refresh(notif)
    return notif

async def mark_all_as_read(db, user_id):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()

async def broadcast_to_all_employees(db, type, title, message):
    res = await db.execute(
        select(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
    )
    employees = res.scalars().all()
    for emp in employees:
        create_notification(db, emp.user_id, type, title, message)
    await db.commit()
