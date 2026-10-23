import os
from datetime import date, datetime, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import (
    Base,
    Comment,
    Meeting,
    Role,
    Task,
    TaskStatus,
    Team,
    TeamUser,
    User,
    UserMeeting,
)
from app.services.auth import (
    create_jwt_token,
    hash_password,
)

TEST_DATABASE_URL = (
    settings.database_url.rsplit('/', 1)[0]
    + f'/team_manager_test'
)

engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

def get_future_date(hour: int | None = None):
    f_date = datetime.now().date() + timedelta(days=2)
    if hour is not None:
        return datetime(
            f_date.year,
            f_date.month,
            f_date.day,
            hour,
        )
    return f_date


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSession(
        bind=engine,
        expire_on_commit=False,
    ) as db:
        db.add_all([
            Role(
                name="manager",
                description="Управляет командой",
            ),
            Role(
                name="member",
                description="Член команды",
            ),
        ])
        await db.commit()

    yield


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_database():
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db():
    async with AsyncSession(
        bind=engine,
        expire_on_commit=False,
    ) as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url='http://test',
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
def user_data():
    USER_DATA = [
        {
            'email': 'test@test.ru',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': '11111111',
            'age': 25,
        },
        {
            'email': 'ivan@test.ru',
            'username': 'ivanuser',
            'first_name': 'Ivan',
            'last_name': 'Ivanov',
            'password': '22222222',
            'age': 30,
        },
        {
            'email': 'anna@test.ru',
            'username': 'annauser',
            'first_name': 'Anna',
            'last_name': 'Petrova',
            'password': '33333333',
            'age': 28,
        },
        {
            'email': 'petr@test.ru',
            'username': 'petruser',
            'first_name': 'Petr',
            'last_name': 'Sidorov',
            'password': '44444444',
            'age': 35,
        },
        {
            'email': 'olga@test.ru',
            'username': 'olgauser',
            'first_name': 'Olga',
            'last_name': 'Smirnova',
            'password': '55555555',
            'age': 22,
        },
    ]
    return USER_DATA


@pytest_asyncio.fixture
async def create_users(user_data, db):
    users = []
    for data in user_data:
        user = User(
            email=data['email'],
            username=data['username'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            password_hash=hash_password(data['password']),
            age=data['age'],
        )
        db.add(user)
        users.append(user)
    await db.commit()
    return users


@pytest_asyncio.fixture
async def create_users_not_in_team(db):
    user = User(
        email='dima@test.ru',
        username='dimauser',
        first_name='Dima',
        last_name='Smirnov',
        password_hash=hash_password('55555555'),
        age=22,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def create_jwt(create_users):
    jwt = create_jwt_token(create_users[0].id)
    return {
        'user': create_users[0],
        'token': jwt,
    }


@pytest_asyncio.fixture
async def create_bad_jwt(create_users):
    jwt = create_jwt_token(create_users[1].id)
    return {
        'user': create_users[1],
        'token': jwt,
    }


@pytest_asyncio.fixture
async def create_super_user(db):
    super_user = User(
        email='seper@user.com',
        username='superuser',
        first_name='Super',
        last_name='User',
        password_hash=hash_password('superuser'),
        age=30,
        is_active=True,
        is_admin=True,
        is_superuser=True,
    )
    db.add(super_user)
    await db.commit()
    await db.refresh(super_user)
    return super_user


@pytest_asyncio.fixture
async def get_super_user_token(create_super_user):
    jwt = create_jwt_token(create_super_user.id)
    return {
        'user': create_super_user,
        'token': jwt,
    }


@pytest_asyncio.fixture
def team_data():
    TEAM_DATA = {
        'name': 'Имя команды',
        'description': 'Описание команды',
        'invite_code': 'password',
    }
    return TEAM_DATA


@pytest_asyncio.fixture
async def create_team(team_data, create_super_user, db):
    manager_role = await db.scalar(
        select(Role).where(Role.name == 'manager')
    )
    team = Team(
        name=team_data['name'],
        description=team_data['description'],
        invite_code=hash_password(team_data['invite_code']),
    )
    db.add(team)
    await db.flush()

    team_user = TeamUser(
        user_id=create_super_user.id,
        team_id=team.id,
        role_id=manager_role.id,
    )
    db.add(team_user)
    await db.commit()
    await db.refresh(team)
    return team


@pytest_asyncio.fixture
async def create_team_with_users(create_team, create_users, db):
    member_role = await db.scalar(
        select(Role).where(Role.name == 'member')
    )
    team_user_list = []
    for user in create_users:
        team_user = TeamUser(
            role_id=member_role.id,
            team_id=create_team.id,
            user_id=user.id,
        )
        db.add(team_user)
        team_user_list.append(team_user)

    await db.commit()
    return {
        'team_obj': create_team,
        'team_user': team_user_list,
    }


@pytest_asyncio.fixture
async def create_second_team_with_users(
    team_data, create_super_user, create_users, db
):
    manager_role = await db.scalar(
        select(Role).where(Role.name == 'manager')
    )
    team = Team(
        name='second_team',
        description=team_data['description'],
        invite_code=hash_password(team_data['invite_code']),
    )
    db.add(team)
    await db.flush()

    team_user = TeamUser(
        user_id=create_super_user.id,
        team_id=team.id,
        role_id=manager_role.id,
    )
    db.add(team_user)
    await db.commit()
    await db.refresh(team)
    member_role = await db.scalar(
        select(Role).where(Role.name == 'member')
    )
    team_user_list = []
    for user in create_users:
        team_user = TeamUser(
            role_id=member_role.id,
            team_id=team.id,
            user_id=user.id,
        )
        db.add(team_user)
        team_user_list.append(team_user)

    await db.commit()
    return {
        'team_obj': team,
        'team_user': team_user_list,
    }


@pytest_asyncio.fixture
def task_data(create_users):
    TASK_DATA = {
        'assignee_id': create_users[0].id,
        'title': 'Важная задача',
        'description': 'Первая важная задача которая создается для спасения человечества',
        'due_date': date.today() + timedelta(weeks=2),
    }
    return TASK_DATA


@pytest_asyncio.fixture
async def create_task(task_data, create_team_with_users, db):
    task = Task(
        team_id=create_team_with_users['team_obj'].id,
        assignee_id=task_data['assignee_id'],
        title=task_data['title'],
        description=task_data['description'],
        due_date=task_data['due_date'],
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@pytest_asyncio.fixture
async def create_comment(create_task, create_jwt, db):
    comment = Comment(
        task_id=create_task.id,
        author_id=create_jwt['user'].id,
        text='Тестовый комментарий',
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return comment


@pytest_asyncio.fixture
async def create_done_task(
    create_task,
    db,
):
    create_task.status = TaskStatus.DONE
    await db.commit()
    await db.refresh(create_task)
    return create_task


@pytest_asyncio.fixture
def meet_data():
    MEET_DATA = {
        'name': 'Планёрка',
        'description': 'Обсуждение задач команды',
        'starts_at': get_future_date(10).isoformat(),
        'ends_at': get_future_date(11).isoformat(),
    }
    return MEET_DATA


@pytest_asyncio.fixture
async def create_meeting(
    create_team_with_users,
    get_super_user_token,
    db,
):
    meeting = Meeting(
        team_id=create_team_with_users['team_obj'].id,
        organizer_id=get_super_user_token['user'].id,
        name='Первая встреча',
        description='Первая встреча',
        starts_at=get_future_date(10),
        ends_at=get_future_date(11),
    )

    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    return meeting


@pytest_asyncio.fixture
async def create_user_meeting(
    create_meeting,
    create_jwt,
    db,
):
    user_meeting = UserMeeting(
        meeting_id=create_meeting.id,
        user_id=create_jwt['user'].id,
    )

    db.add(user_meeting)
    await db.commit()

    return create_meeting
