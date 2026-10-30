from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.teams import get_role
from app.database import get_db
from app.dependencies.task import get_task_obj_with_user_obj
from app.models import Role, Task, TeamUser, User
from app.services.auth import get_current_user
from app.services.handlers import PermissionDeniedException

MANAGER = 'manager'
MEMBER = 'member'


async def get_manager_role(
    db: AsyncSession = Depends(get_db),
) -> Role:
    role_name = MANAGER
    role = await get_role(role_name, db)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Не инициализированы базове роли'
        )
    return role


async def get_member_role(
    db: AsyncSession = Depends(get_db),
) -> Role:
    role_name = MEMBER
    role = await get_role(role_name, db)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Не инициализированы базове роли'
        )
    return role


async def get_current_manager_by_task(
    task: Task = Depends(get_task_obj_with_user_obj),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    manager = await db.scalar(
        select(TeamUser.id)
        .join(Role, TeamUser.role_id == Role.id)
        .where(
            TeamUser.team_id == task.team_id,
            TeamUser.user_id == user.id,
            Role.name == MANAGER,
        )
    )
    if manager is None:
        raise PermissionDeniedException(
            'Действие доступно только менеджеру команды'
        )
    return user


async def get_current_manager_by_team(
    team_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    manager = await db.scalar(
        select(TeamUser.id)
        .join(Role, TeamUser.role_id == Role.id)
        .where(
            TeamUser.team_id == team_id,
            TeamUser.user_id == user.id,
            Role.name == MANAGER,
        )
    )
    if manager is None:
        raise PermissionDeniedException(
            'Действие доступно только менеджеру команды'
        )
    return user
