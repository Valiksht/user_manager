from datetime import datetime, timedelta, timezone

from fastapi import (
    HTTPException,
)

from app.crud.meetings import (
    add_user_list_from_meeting,
    exist_meeting_team,
    exist_meeting_user,
    get_meet_list_team,
    get_meet_list_user,
    get_meet_by_id,
    get_user_meet_id_by_id,
    get_user_meet_small_obj_by_id,
    remove_user_list_from_meeting,
    update_meet,
)
from app.crud.tasks import (
    get_task_list_user_with_date,
)
from app.crud.teams import get_user_in_team
from app.models import (
    Meeting,
    UserMeeting,
)
from app.services.handlers import PermissionDeniedException
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
    if meet_data.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail='Время начала должно быть позже текущего времени',
        )
    if (meet_data.ends_at - meet_data.starts_at) >= timedelta(hours=8):
        raise HTTPException(
            status_code=400,
            detail='Встреча не может длиться больше 8 часов',
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
        members_meet_id, meet_data.starts_at, meet_data.ends_at, db
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


async def meet_update(meet_id, meet_data, user, db):
    meet = await get_meet_by_id(meet_id, db)
    if meet.organizer_id != user.id:
        raise PermissionDeniedException(
            'Изменить встречу может только организатор'
        )
    update_data = meet_data.model_dump(exclude_unset=True)
    users_add = update_data.pop('users_add', None)
    users_remove = update_data.pop('users_remove', None)
    current_starts_at = meet.starts_at
    current_ends_at = meet.ends_at
    if 'starts_at' in update_data:
        if meet_data.starts_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail='Время начала должно быть позже текущего времени',
            )
        current_starts_at = update_data.get('starts_at')
    if 'ends_at' in update_data:
        if meet_data.ends_at <= current_starts_at:
            raise HTTPException(
                status_code=400,
                detail='Время окончания должно быть позже времени начала',
            )
        current_ends_at = update_data.get('ends_at')
    if (current_ends_at - current_starts_at) > timedelta(hours=8):
        raise HTTPException(
            status_code=400,
            detail='Встреча не может длиться больше 8 часов',
        )
    try:
        meet = await update_meet(meet, update_data, db)
        if users_remove:
            await remove_user_list_from_meeting(
                meet.id, users_remove, db
            )
        meet_users_list = (
            await get_user_meet_id_by_id(meet_id, db)
        ).all()
        if users_add:
            duplicate_user = set(users_add) & set(meet_users_list)
            if duplicate_user:
                raise HTTPException(
                    status_code=409,
                    detail=f'Пользователи с id {list(duplicate_user)} уже являются участниками встречи',
                )
            meet_users_list.extend(users_add)

        exist_meet = await exist_meeting_user(
            meet_users_list,
            current_starts_at,
            current_ends_at,
            db,
            meet.id,
        )
        if exist_meet:
            raise HTTPException(
                status_code=409,
                detail='Время встречи пересекается с существующей встречей учасника встречи',
            )
        if users_add:
            await add_user_list_from_meeting(meet.id, users_add, db)
        await db.commit()
        users = await get_user_meet_small_obj_by_id(meet.id, db)
        meet.users = users.all()
        return meet
    except Exception as e:
        await db.rollback()
        raise e
