from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.meerings import router as meet_router
from app.api.tasks import router as task_router
from app.api.teams import router as team_router
from app.api.users import auth_router, user_router
from app.config import settings
from app.database import DATABASE_URL, get_db
from app.services.hendlers import (
    AppExeption,
    app_exeprion_hendler,
)
from app.services.create_role import create_role


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.DEBUG,
    )
    app.state.enfine = engine
    app.state.session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
    await create_role()
    yield
    await engine.dispose()


app = FastAPI(
    title='Team Manager API',
    description='''
    API для управления командами, пользователями и рабочими процессами.

    Основные возможности:

    - регистрация и аутентификация пользователей;
    - управление командами;
    - управление участниками команд;
    - создание и назначение задач;
    - планирование встреч;
    - комментарии к задачам;
    - оценка выполненных задач.
    ''',
    version='1.0.0',
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(team_router)
app.include_router(task_router)
app.include_router(meet_router)

app.add_exception_handler(
    AppExeption, app_exeprion_hendler
)


@app.get('/health')
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text('SELECT 1'))
    return {'status': 'ok'}


@app.exception_handler(IntegrityError)
async def integrity_error_hendler(
    request: Request,
    exc: IntegrityError,
):
    return JSONResponse(
        status_code=409,
        content={
            'detail': 'Объект с такими данными уже существует'
        },
    )
