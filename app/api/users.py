from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth import (
    create_jwt_token,
    get_id_from_token,
    hash_password,
    verify_password,
)
from app.services.hendlers import (
    NotFoundItemExeption,
    PermissionDeniedExeption,
)

auth_router = APIRouter(prefix='/auth', tags=['Auth'])

user_router = APIRouter(
    prefix='/users',
    tags=['User'],
)


@auth_router.post(
    '/register',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Зарегистрировать пользователя.',
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Зарегистрировать нового пользователя.
    
    Создаёт пользователя с указанными регистрационными данными.
    Email и username должны быть уникальными.
    Пароль сохраняется в виде хеша.
    """
    user_exist = await db.scalar(
        select(User).where(
            (User.email == user_data.email)
            | (User.username == user_data.username)
        )
    )
    if user_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email или username уже занят',
        )
    user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        password_hash=hash_password(user_data.password),
        age=user_data.age,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@auth_router.post(
    '/login',
    response_model=Token,
    summary='Авторизовать пользователя.',
)
async def login(
    user_data: UserLogin, db: AsyncSession = Depends(get_db)
):
    """
    Авторизовать пользователя и получить JWT-токен.
    
    Для авторизации необходимо передать корректные email и пароль.
    В ответ возвращается Bearer-токен, который используется для доступа
    к защищённым endpoint'ам приложения.
    """
    user_exist = await db.scalar(
        select(User).where(User.email == user_data.email)
    )
    if not user_exist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный email или пароль',
        )
    if not user_exist.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Аккаунт отключен',
        )
    password_is_valid = verify_password(
        user_data.password, user_exist.password_hash
    )
    if password_is_valid:
        return create_jwt_token(user_exist.id)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Неверный email или пароль',
    )


@user_router.get(
    '/me',
    response_model=UserResponse,
    summary='Получить данные текущего пользователя.',
)
async def get_current_user(
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить информацию о пользователе, выполнившем авторизацию.
    
    Пользователь определяется по идентификатору из JWT-токена.
    Отключённые пользователи не могут получить свои данные.
    """
    user = await db.scalar(
        select(User).where(
            User.id == user_id, User.is_active == True
        )
    )
    if not user:
        raise NotFoundItemExeption(
            'Пользователь не найден или отключен'
        )
    return user


@user_router.get(
    '',
    response_model=list[UserResponse],
    summary='Получить всех пользователей.',
)
async def all_users(
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список всех зарегистрированных пользователей приложения.
    
    В ответ возвращается список пользователей без их паролей 
    и других чувствительных данных.
    """
    users = (await db.scalars(select(User))).all()
    return users


@user_router.post(
    '/{user_id}/admin',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Назначить пользователя администратором.',
)
async def make_admin(
    user_id: int,
    current_user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Назначить указанного пользователя администратором приложения.
    
    Операция доступна только пользователю с правами superuser.
    После выполнения операции у указанного пользователя устанавливается
    признак администратора (is_admin).
    Пользователи с правами администрора считаются начальниками отделов.
    У них есть возможность создавать команды.
    """
    current_user = await db.scalar(
        select(User).where(User.id == current_user_id)
    )
    if not current_user:
        raise NotFoundItemExeption('Пользователь не найден')
    if not current_user.is_superuser:
        raise PermissionDeniedExeption(
            'Только superuser может назначать администратора'
        )
    user = await db.scalar(
        select(User).where(User.id == user_id)
    )
    if not user:
        raise NotFoundItemExeption(
            f'Пользователь с id {user_id} не найден'
        )
    user.is_admin = True
    await db.commit()
    await db.refresh(user)
    return user
