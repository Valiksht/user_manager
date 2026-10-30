import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import DATABASE_URL
from app.models import User
from app.services.auth import hash_password

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

parser = argparse.ArgumentParser(description="Создание суперпользователя")
parser.add_argument('--email', help="Email суперпользователя")
parser.add_argument('--username', help="Имя пользователя")
parser.add_argument('--password', help="Пароль")


async def create_superuser():
    args = parser.parse_args()
    async with async_session_factory() as db:
        email = args.email or input("Введите email: ")
        username = args.username or input("Введите username: ")
        password = args.password or input("Введите пароль: ")
        existing_user = await db.scalar(
            select(User).where(
                (User.email == email) | (User.username == username)
            )
        )

        if existing_user:
            print('Email или username уже заняты')
            return

        user = User(
            email=email,
            username=username,
            first_name='Super',
            last_name='User',
            password_hash=hash_password(password),
            is_active=True,
            is_admin=True,
            is_superuser=True,
        )

        db.add(user)
        await db.commit()

        print(f'Superuser {username} - успешно создан!')


if __name__ == '__main__':
    asyncio.run(create_superuser())
