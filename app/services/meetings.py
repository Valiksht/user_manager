from datetime import datetime

from fastapi import (
    HTTPException,
)

from app.crud.meetings import (
    exist_meeting_team,
    exist_meeting_user,
    get_meet_list_team,
    get_meet_list_user,
)
from app.crud.tasks import (
    get_task_list_user_with_date,
)
from app.crud.teams import get_user_in_team
from app.models import (
    Meeting,
    UserMeeting,
)
from app.schemas import CalendarResponse
from app.services.handlers import (
    NotFoundItemException,
)


async def meet_list_team(starts_at, ends_at, user_id, db):
    meetings = await get_meet_list_team(starts_at, ends_at, user_id, db)
    meetings = meetings.all()
    for meeting in meetings:
        meeting.users = [
            participant.user for participant in meeting.participants
        ]
    return meetings


async def meet_list_user(starts_at, ends_at, user_id, db):
    meetings = await get_meet_list_user(starts_at, ends_at, user_id, db)
    meetings = meetings.all()
    for meeting in meetings:
        meeting.users = [
            participant.user for participant in meeting.participants
        ]

    return meetings


async def meet_and_task_list(starts_at, ends_at, user_id, db):
    meet_list = await meet_list_user(starts_at, ends_at, user_id, db)
    task_list = await get_task_list_user_with_date(
        user_id, db, starts_at, ends_at
    )
    response = CalendarResponse(
        meetings=meet_list,
        tasks=task_list,
    )
    return response


async def create_new_meet(meet_data, team_id, user_creator, db):
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

    users_in_team = (await get_user_in_team(team_id, db)).all()
    users_in_team_id = [user.id for user in users_in_team]
    if meet_data.users is not None:
        for member_id in meet_data.users:
            if member_id not in users_in_team_id:
                raise NotFoundItemException(
                    f'Пользователь с id {member_id} не состоит в команде или не существует'
                )
        members_meet_id = meet_data.users
    else:
        members_meet_id = users_in_team_id

    if user_creator.id not in members_meet_id:
        members_meet_id.append(user_creator.id)

    existing_meeting_team = await exist_meeting_team(
        team_id, meet_data, db
    )
    if existing_meeting_team:
        raise HTTPException(
            status_code=409,
            detail='Время встречи пересекается с существующей встречей в команде',
        )

    existing_meeting_user = await exist_meeting_user(
        members_meet_id, meet_data, db
    )
    if existing_meeting_user:
        raise HTTPException(
            status_code=409,
            detail='Время встречи пересекается с существующей встречей учасника встречи',
        )

    meeting = Meeting(
        team_id=team_id,
        organizer_id=user_creator.id,
        name=meet_data.name,
        description=meet_data.description,
        starts_at=meet_data.starts_at,
        ends_at=meet_data.ends_at,
    )
    db.add(meeting)
    await db.flush()
    current_members_meet = []
    user_by_id = {user.id: user for user in users_in_team}
    for user_id in members_meet_id:
        user_meeting = UserMeeting(
            user_id=user_id,
            meeting_id=meeting.id,
        )
        db.add(user_meeting)
        current_members_meet.append(user_by_id[user_id])
    await db.commit()
    await db.refresh(meeting)
    meeting.users = current_members_meet
    return meeting
