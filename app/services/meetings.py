from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.meetings import exist_meeting, get_meet_list_team, get_meet_list_user
from app.crud.teams import get_user_in_team
from app.database import get_db
from app.models import (
    Meeting,
    Role,
    Team,
    TeamUser,
    User,
    UserMeeting,
)
from app.schemas import (
    MeetCreate,
    MeetResponse,
)
from app.services.auth import (
    get_current_user,
)
from app.services.hendlers import (
    NotFoundItemExeption,
    PermissionDeniedExeption,
)

async def meet_list_team(starts_at, ends_at, user_id, db):
    meetings = await get_meet_list_team(
        starts_at, ends_at, user_id, db
    )
    meetings = meetings.all()
    for meeting in meetings:
        meeting.users = [
            participant.user
            for participant in meeting.participants
        ]
    return meetings

async def meet_list_user(starts_at, ends_at, user_id, db):
    meetings = await get_meet_list_user(starts_at, ends_at, user_id, db)
    meetings = meetings.all()
    for meeting in meetings:
        meeting.users = [
            participant.user
            for participant in meeting.participants
        ]

    return meetings

async def create_new_meet(meet_data, team_id, user_id, db):
    if meet_data.ends_at <= meet_data.starts_at:
        raise HTTPException(
            status_code=400,
            detail='Время окончания должно быть позже времени начала',
        )
    if meet_data.starts_at <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail='Время начала должно быть позже текущего времени',
        )
    existing_meeting = await exist_meeting(team_id, meet_data, db)
    if existing_meeting:
        raise HTTPException(
            status_code=409,
            detail='Время встречи пересекается с существующей встречей',
        )
    meeting = Meeting(
        team_id=team_id,
        organizer_id=user_id,
        name=meet_data.name,
        description=meet_data.description,
        starts_at=meet_data.starts_at,
        ends_at=meet_data.ends_at,
    )
    db.add(meeting)
    await db.flush()
    members_meet = (
        await get_user_in_team(team_id, db)
    ).all()
    if meet_data.users is not None:
        members_by_id = {
            member.id: member for member in members_meet
        }
        current_members_meet = []
        print(meet_data.users)
        members_ids = {member.id for member in members_meet}
        for member_id in meet_data.users:
            if member_id not in members_ids:
                raise NotFoundItemExeption(
                    f'Пользователь с id {member_id} не состоит в команде или не существует'
                )
            user_meeting = UserMeeting(
                user_id=member_id,
                meeting_id=meeting.id,
            )
            db.add(user_meeting)
            current_members_meet.append(
                members_by_id[member_id]
            )
    else:
        current_members_meet = members_meet
        for member in members_meet:
            user_meeting = UserMeeting(
                user_id=member.id,
                meeting_id=meeting.id,
            )
            db.add(user_meeting)

    await db.commit()
    await db.refresh(meeting)
    meeting.users = current_members_meet
    return meeting

