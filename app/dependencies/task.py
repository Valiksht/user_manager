from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.tasks import (
    get_task_obj_with_user_in_team,
    get_task_with_team_id,
)
from app.database import get_db
from app.models import User
from app.services.auth import get_id_from_token
from app.services.hendlers import NotFoundItemExeption


async def get_task_obj_with_team_id(
    task_id: int,
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_with_team_id(task_id, team_id, db)
    return task


async def get_task_obj_with_user_odj(
    task_id: int,
    user_id: User = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_obj_with_user_in_team(task_id, user_id, db)
    if not task:
        raise NotFoundItemExeption('Задача не найдена')
    return task
