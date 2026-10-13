from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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

router = APIRouter(prefix='/calendar', tags=['Meeteng'])


@router.get(
    '',
    response_model=list[MeetResponse],
    summary='Получить календарь пользователя.',
)
async def meet(
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список встреч команд, в которых состоит текущий пользователь.

    Можно дополнительно указать временной диапазон с помощью параметров
    starts_at и ends_at.

    В ответе возвращается информация о встречах и их участниках.
    """
    query = (
        select(Meeting)
        .join(TeamUser, Meeting.team_id == TeamUser.team_id)
        .where(
            TeamUser.user_id == user.id,
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
    meetings = meetings.all()
    for meeting in meetings:
        meeting.users = [
            participant.user
            for participant in meeting.participants
        ]

    return meetings


@router.get(
    '/me',
    response_model=list[MeetResponse],
    summary='Получить свои встречи.',
)
async def me_meet(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список встреч, участником которых является текущий пользователь.

    В ответе возвращаются встречи, в которые текущий пользователь
    был добавлен как участник.
    """
    meetings = await db.scalars(
        select(Meeting)
        .join(
            UserMeeting,
            Meeting.id == UserMeeting.meeting_id,
        )
        .where(UserMeeting.user_id == user.id)
        .options(
            selectinload(Meeting.participants).selectinload(
                UserMeeting.user
            )
        )
    )
    meetings = meetings.all()
    for meeting in meetings:
        meeting.users = [
            participant.user
            for participant in meeting.participants
        ]

    return meetings


@router.post(
    '/{team_id}',
    response_model=MeetResponse,
    summary='Создать встречу для команды.',
)
async def create_meet(
    team_id: int,
    meet_data: MeetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую встречу для указанной команды.
    
    Создавать встречи может только менеджер команды.
    
    Время окончания должно быть позже времени начала,
    а время начала не может быть в прошлом.
    Встреча не может пересекаться по времени с другой встречей этой команды.
    
    Можно указать конкретных участников встречи.
    Если список участников не указан, в встречу добавляются все участники команды.
    """
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
    team = await db.scalar(
        select(Team).where(Team.id == team_id)
    )
    if not team:
        raise NotFoundItemExeption('Команда не найдена')
    manager = await db.scalar(
        select(TeamUser)
        .join(Role, TeamUser.role_id == Role.id)
        .where(
            TeamUser.user_id == user.id,
            TeamUser.team_id == team_id,
            Role.name == 'manager',
        )
    )
    if not manager:
        raise PermissionDeniedExeption(
            'Только менеджер может создать встречу'
        )
    existing_meeting = await db.scalar(
        select(Meeting).where(
            Meeting.team_id == team_id,
            Meeting.starts_at < meet_data.ends_at,
            Meeting.ends_at > meet_data.starts_at,
        )
    )
    if existing_meeting:
        raise HTTPException(
            status_code=409,
            detail='Время встречи пересекается с существующей встречей',
        )
    meeting = Meeting(
        team_id=team_id,
        organizer_id=user.id,
        name=meet_data.name,
        description=meet_data.description,
        starts_at=meet_data.starts_at,
        ends_at=meet_data.ends_at,
    )
    db.add(meeting)
    await db.flush()
    members_meet = (
        await db.scalars(
            select(User)
            .join(TeamUser, User.id == TeamUser.user_id)
            .where(TeamUser.team_id == team_id)
        )
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
