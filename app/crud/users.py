from fastapi import HTTPException, status
from sqlalchemy import select

from app.models import User
from app.services.hendlers import NotFoundItemExeption


async def get_user_from_email_or_username(user_data, db):
    email = getattr(user_data, 'email', None)
    username = getattr(user_data, 'username', None)
    if email and username:
        query = select(User).where(
            (User.email == email) | (User.username == username)
        )
    elif email:
        query = select(User).where(User.email == email)
    elif username:
        query = select(User).where(User.username == username)
    else:
        raise ValueError('Необходимо передать email или username')
    return await db.scalar(query)


async def get_user_deteil(user_id, db):
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='не передан "user_id"',
        )
    user = await db.scalar(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    if user is None:
        raise NotFoundItemExeption(
            f'Пользователь с id {user_id} не найден'
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Пользователь деактивирован',
        )
    return user


async def get_user_list(db):
    user_list = (await db.scalars(select(User))).all()
    return user_list
