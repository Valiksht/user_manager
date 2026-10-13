from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.config import settings


DATABASE_URL = settings.database_url


async def get_db(
    requst: Request,
) -> AsyncGenerator[AsyncSession, None]:
    sessin_factory: async_sessionmaker[AsyncSession] = (
        requst.app.state.session_factory
    )

    async with sessin_factory() as session:
        yield session
