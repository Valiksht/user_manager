from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.tasks import (
    get_comment_by_id,
    get_task_obj_with_user_in_team,
    get_task_with_team_id,
)
from app.database import get_db
from app.models import User
from app.services.auth import get_id_from_token
from app.services.handlers import NotFoundItemException


async def get_task_obj_with_team_id(
    task_id: int,
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_with_team_id(task_id, team_id, db)
    return task


async def get_task_obj_with_user_obj(
    task_id: int,
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_obj_with_user_in_team(task_id, user_id, db)
    if not task:
        raise NotFoundItemException('Задача не найдена')
    return task

async def get_comment_obj(
    task_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
):
    if comment_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='не передан id коментария'
        )
    comment = await get_comment_by_id(comment_id, task_id, db)
    if comment is None:
        raise NotFoundItemException(
            'Комментарий не найден или не существует'
        ) 
    return comment  
