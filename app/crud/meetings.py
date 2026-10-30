from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.models import Meeting, TeamUser, User, UserMeeting
from app.services.handlers import NotFoundItemException


async def get_meet_by_id(meet_id, db):
    meet = await db.scalar(select(Meeting).where(Meeting.id == meet_id))
    if meet is None:
        raise NotFoundItemException('Встерча не найдена')
    return meet

async def get_user_meet_id_by_id(meet_id, db):
    user_meet = await db.scalars(
        select(UserMeeting.user_id).where(
            UserMeeting.meeting_id == meet_id
        )
    )
    return user_meet

async def get_user_meet_small_obj_by_id(meet_id, db):
    user_meet = await db.execute(
        select(
            User.id,
            User.username,
            User.first_name,
            User.last_name
        ).join(
            UserMeeting, User.id == UserMeeting.user_id
        ).where(
            UserMeeting.meeting_id == meet_id
        )
    )
    return user_meet.mappings()


async def update_meet(meet, update_data, db):
    for field, value in update_data.items():
        setattr(meet, field, value)
    await db.flush()
    return meet


async def add_user_list_from_meeting(meeting_id, user_id_list, db):
    for user_id in user_id_list:
        user_meeting = UserMeeting(
            user_id=user_id, meeting_id=meeting_id
        )
        db.add(user_meeting)
    await db.flush()


async def remove_user_list_from_meeting(meeting_id, user_id_list, db):
    await db.execute(
        delete(UserMeeting).where(
            UserMeeting.meeting_id == meeting_id,
            UserMeeting.user_id.in_(user_id_list),
        )
    )
    await db.flush()


async def get_meet_list_team(starts_at, ends_at, user_id, db):
    query = (
        select(Meeting)
        .join(TeamUser, Meeting.team_id == TeamUser.team_id)
        .where(
            TeamUser.user_id == user_id,
        )
        .options(
            selectinload(Meeting.participants).selectinload(
                UserMeeting.user
            )
        )
    )
    if starts_at:
        query = query.where(Meeting.starts_at >= starts_at)
    if ends_at:
        query = query.where(Meeting.ends_at <= ends_at)
    meetings = await db.scalars(query)
    return meetings


async def get_meet_list_user(starts_at, ends_at, user_id, db):
    query = (
        select(Meeting)
        .join(
            UserMeeting,
            Meeting.id == UserMeeting.meeting_id,
        )
        .where(UserMeeting.user_id == user_id)
        .options(
            selectinload(Meeting.participants).selectinload(
                UserMeeting.user
            )
        )
    )
    if starts_at:
        query = query.where(Meeting.starts_at >= starts_at)
    if ends_at:
        query = query.where(Meeting.ends_at <= ends_at)
    meetings = await db.scalars(query)
    return meetings


async def exist_meeting_team(team_id, meet_data, db):
    meet = await db.scalar(
        select(Meeting).where(
            Meeting.team_id == team_id,
            Meeting.starts_at < meet_data.ends_at,
            Meeting.ends_at > meet_data.starts_at,
        )
    )
    return meet


async def exist_meeting_user(
    members_meet_id, starts_at, ends_at, db, exclude_meet_id=None
):
    query = (
        select(Meeting.id)
        .join(
            UserMeeting,
            UserMeeting.meeting_id == Meeting.id,
        )
        .where(
            UserMeeting.user_id.in_(members_meet_id),
            Meeting.starts_at < ends_at,
            Meeting.ends_at > starts_at,
        )
    )
    if exclude_meet_id is not None:
        query = query.where(Meeting.id != exclude_meet_id)
    meet = await db.scalar(query.limit(1))
    return meet
