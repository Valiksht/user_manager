from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Team
from app.services.handlers import NotFoundItemException


async def get_team_obj(
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    if not team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='не передан "team_id"',
        )
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id,
        )
    )
    if team is None:
        raise NotFoundItemException(
            f'Команда с id {team_id} не найдена'
        )
    return team
