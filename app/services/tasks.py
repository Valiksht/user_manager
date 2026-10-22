from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.tasks import (
    get_comment_from_task_id,
    get_evaluation,
    get_task_id_with_user_in_team,
    get_task_list_user,
    get_task_with_details,
)
from app.crud.tasks import (
    get_user_evaluation_list as evaluation_list,
)
from app.crud.teams import (
    get_team_by_name,
    get_team_members,
    get_team_with_user,
    user_in_team,
)
from app.database import get_db
from app.dependencies.role import get_manager_role
from app.models import (
    Comment,
    Evaluation,
    Role,
    Task,
    TaskStatus,
    Team,
    TeamUser,
    User,
)
from app.schemas import (
    RoleInTeamResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TeamCreate,
    TeamJoin,
    TeamJoinResponse,
    TeamResponseDetail,
    TeamResponseList,
    UserResponse,
)
from app.services.auth import (
    get_current_admin,
    get_current_user,
    get_id_from_token,
    hash_password,
    verify_password,
)
from app.services.hendlers import (
    NotFoundItemExeption,
    PermissionDeniedExeption,
)


async def create_new_tast(task_data, team_id, user_id, db):
    exist_user = await user_in_team(team_id, user_id, db)
    if not exist_user:
        raise PermissionDeniedExeption(
            'Вы не состоите в данной команде'
        )
    manager_role = await get_manager_role(db)
    if exist_user.role_id != manager_role.id:
        raise PermissionDeniedExeption(
            'Вы не можете создавать задачи для этой команды'
        )
    current_team = await user_in_team(
        team_id, task_data.assignee_id, db
    )
    if not current_team:
        raise NotFoundItemExeption(
            'Назначаемый пользователь не состоит в этой команде'
        )
    if task_data.due_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Дата выполнения не может быть раньше текущей',
        )
    task = Task(
        team_id=team_id,
        assignee_id=task_data.assignee_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(task_data, team_id, user_id, task, db):
    exist_user = await user_in_team(team_id, user_id, db)
    if not exist_user:
        raise PermissionDeniedExeption(
            'Вы не состоите в данной команде'
        )
    manager_role = await get_manager_role(db)
    perission = exist_user.role_id == manager_role.id
    update_data = task_data.model_dump(exclude_unset=True)

    if not perission and task.assignee_id != user_id:
        raise PermissionDeniedExeption(
            'Вы не можете изменить эту задачу'
        )
    update_data = task_data.model_dump(exclude_unset=True)
    if not perission and not set(update_data).issubset(
        {'status'}
    ):
        raise PermissionDeniedExeption(
            'Вы можете изменить только статус задачи'
        )

    if 'assignee_id' in update_data and update_data['assignee_id']:
        current_team = await user_in_team(
            team_id, task_data.assignee_id, db
        )
        if not current_team:
            raise NotFoundItemExeption(
                'Назначаемый пользователь не состоит в этой команде'
            )
    if (
        'due_date' in update_data
        and update_data['due_date'] is not None
        and update_data['due_date'] < date.today()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Дата выполнения не может быть раньше текущей',
        )


    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task

async def task_detail(task_id, user_id, db):
    depends_user = await get_task_id_with_user_in_team(task_id, user_id, db)
    if not depends_user:
        raise PermissionDeniedExeption(
            'Вы не можете просматривать информацию о этой задаче'
        )
    task = await get_task_with_details(task_id, db)
    return task

async def task_for_user(user_id, db):
    task = await get_task_list_user(user_id, db)
    return task

async def create_task_comment(comment_data, task_id, user_id, db):
    comment = Comment(
        task_id=task_id,
        author_id=user_id,
        text=comment_data.text,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment

async def get_task_comment_list(task_id, db):
    comments = await get_comment_from_task_id(task_id, db)
    return comments

async def create_task_evaluation(evaluation_data, task, user, db):
    if task.status != TaskStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Нельзя оцениварь невыполненые задчи',
        )
    evaluation = Evaluation(
        task_id=task.id,
        user_id=task.assignee_id,
        manager_id=user.id,
        score=evaluation_data.score,
        comment=evaluation_data.comment,
    )
    db.add(evaluation)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Эта задача уже имеет оценку',
        )
    await db.refresh(evaluation)
    return evaluation

async def get_task_evaluation(task_id, db):
    evaluation = await get_evaluation(task_id, db)
    return evaluation

async def get_user_evaluation_list(user_id, db):
    evaluations = await evaluation_list(user_id, db)
    if not evaluations:
        return []
    return evaluations
