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
from app.dependencies.role import get_curret_manager_by_team
from app.dependencies.team import get_team_obj
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
from app.services.meetings import (
    create_new_meet,
    meet_list_team,
    meet_list_user,
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
    return await meet_list_team(starts_at, ends_at, user.id, db)


@router.get(
    '/me',
    response_model=list[MeetResponse],
    summary='Получить свои встречи.',
)
async def me_meet(
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список встреч, участником которых является текущий пользователь.

    В ответе возвращаются встречи, в которые текущий пользователь
    был добавлен как участник.
    """
    return await meet_list_user(starts_at, ends_at, user.id, db)


@router.post(
    '/{team_id}',
    response_model=MeetResponse,
    summary='Создать встречу для команды.',
)
async def create_meet(
    meet_data: MeetCreate,
    team: Team = Depends(get_team_obj),
    user: User = Depends(get_curret_manager_by_team),
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
    return await create_new_meet(meet_data, team.id, user.id, db)
