from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.users import (
    check_user_unique,
    check_user_password,
    get_user_obj_by_id,
)
from app.models import User
from app.schemas import (
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth import (
    get_current_superuser,
    get_id_from_token,
)
from app.services.users import (
    create_user,
    get_token,
    get_user_detail,
    get_user_list,
    update_user_from_admin,
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
    user_data: UserCreate = Depends(check_user_unique),
    db: AsyncSession = Depends(get_db),
):
    """
    Зарегистрировать нового пользователя.

    Создаёт пользователя с указанными регистрационными данными.
    Email и username должны быть уникальными.
    Пароль сохраняется в виде хеша.
    """
    return await create_user(user_data, db)


@auth_router.post(
    '/login',
    response_model=Token,
    summary='Авторизовать пользователя.',
)
async def login(user: User = Depends(check_user_password)):
    """
    Авторизовать пользователя и получить JWT-токен.

    Для авторизации необходимо передать корректные email и пароль.
    В ответ возвращается Bearer-токен, который используется для доступа
    к защищённым endpoint'ам приложения.
    """
    return get_token(user)


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
    return await get_user_detail(user_id, db)


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
    return await get_user_list(db)


@user_router.post(
    '/{user_id}/admin',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Назначить пользователя администратором.',
)
async def make_admin(
    user: User = Depends(get_user_obj_by_id),
    superuser: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Назначить указанного пользователя администратором приложения.

    Операция доступна только пользователю с правами superuser.
    После выполнения операции у указанного пользователя устанавливается
    признак администратора (is_admin).
    Пользователи с правами администратора считаются начальниками отделов.
    У них есть возможность создавать команды.
    """
    return await update_user_from_admin(user, db)
