from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.services.hendlers import (
    NotFoundItemExeption,
    PermissionDeniedExeption,
)

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


oauth2_sheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


async def get_id_from_token(
    token: str = Depends(oauth2_sheme),
):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub = payload.get('sub')
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Невалидный JWT токен',
            )
        return int(sub)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Невалидный JWT токен',
        )


def create_jwt_token(user_id: int):
    if settings.DEBUG:
        jwt_token_life = settings.JWT_TOKEN_LIFE_MINUTES_DEBUD
    else:
        jwt_token_life = settings.JWT_TOKEN_LIFE_MINUTES
    payload = {
        'sub': str(user_id),
        'exp': datetime.now(timezone.utc)
        + timedelta(minutes=jwt_token_life),
    }
    encode = jwt.encode(
        payload,
        settings.SECRET_KEY,
        settings.JWT_ALGORITHM,
    )
    return {'access_token': encode, 'token_type': 'Bearer'}


async def get_current_user(
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.scalar(select(User).where(User.id == user_id))
    if User is None:
        raise NotFoundItemExeption(
            f'Пользователь с id {user_id} не найден'
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Пользователь деактивирован',
        )
    return user


async def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Недостаточно прав',
        )
    return user


async def get_current_superuser(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_superuser:
        raise PermissionDeniedExeption(
            'Операция доступна только пользователю с правами superuser'
        )
    return user
