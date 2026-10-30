import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import DATABASE_URL
from app.models import Role

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

BASE_ROLE = (
    {
        'name': 'manager',
        'description': 'Управляет командой',
    },
    {
        'name': 'member',
        'description': 'Член команды',
    },
)


async def create_role():
    async with async_session_factory() as db:
        for role_data in BASE_ROLE:
            role = await db.scalar(
                select(Role).where(Role.name == role_data['name'])
            )

            if role:
                continue

            db.add(Role(**role_data))

        await db.commit()


if __name__ == '__main__':
    asyncio.run(create_role())