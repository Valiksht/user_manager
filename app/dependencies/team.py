from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Team
from app.services.hendlers import NotFoundItemExeption


async def get_team_obj(
    team_id: int,
    db: AsyncSession = Depends(get_db),
):
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id,
        )
    )
    if not team:
        raise NotFoundItemExeption('Команды не существует')   
    return team
