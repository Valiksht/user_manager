from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Meeting, TeamUser, UserMeeting


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


async def exist_meeting_user(members_meet_id, meet_data, db):
    meet = await db.scalar(
        select(Meeting.id)
        .join(
            UserMeeting,
            UserMeeting.meeting_id == Meeting.id,
        )
        .where(
            UserMeeting.user_id.in_(members_meet_id),
            Meeting.starts_at < meet_data.ends_at,
            Meeting.ends_at > meet_data.starts_at,
        )
        .limit(1)
    )
    return meet
