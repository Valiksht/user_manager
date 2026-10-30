from fastapi import (
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.users import (
    get_user_from_email_or_username,
)
from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate,
    UserLogin,
)
from app.services.auth import (
    verify_password,
)
from app.services.users import get_user_detail


async def check_user_unique(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    user_exist = await get_user_from_email_or_username(user_data, db)
    if user_exist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Email или username уже заняты',
        )
    return user_data


async def check_user_password(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_exist = await get_user_from_email_or_username(user_data, db)
    if not user_exist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный email или пароль',
        )
    if not user_exist.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Аккаунт отключён',
        )
    password_is_valid = verify_password(
        user_data.password, user_exist.password_hash
    )
    if password_is_valid:
        return user_exist
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Неверный email или пароль',
    )


async def get_user_obj_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> User:
    user_obj = await get_user_detail(user_id, db)
    return user_obj
