from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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
    CommentCreate,
    CommentResponse,
    EvaluationCreate,
    EvaluationResponse,
    TaskResponse,
)
from app.services.auth import (
    get_current_user,
    get_id_from_token,
)
from app.services.hendlers import (
    NotFoundItemExeption,
    PermissionDeniedExeption,
)

router = APIRouter(prefix='/tasks', tags=['Task'])


@router.get(
    '',
    response_model=list[TaskResponse],
    summary='Получить свои задачи.',
)
async def get_my_tasks(
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список задач, назначенных текущему пользователю.

    В ответ возвращаются все задачи, исполнителем которых является
    авторизованный пользователь.
    """
    tasks = await db.scalars(
        select(Task).where(Task.assignee_id == user_id)
    )
    return tasks


@router.post(
    '/{task_id}/comments',
    response_model=CommentResponse,
    summary='Добавить комментарий к задаче.',
)
async def task_comment(
    task_id: int,
    comment_data: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Добавить комментарий к указанной задаче.
    
    Добавлять комментарии могут только участники команды,
    к которой относится задача.
    Комментарий сохраняется с указанием автора.
    """
    task = await db.scalar(
        select(Task)
        .join(TeamUser, Task.team_id == TeamUser.team_id)
        .where(
            Task.id == task_id, TeamUser.user_id == user.id
        )
    )
    if not task:
        raise NotFoundItemExeption('Задача не найдена')
    comment = Comment(
        task_id=task_id,
        author_id=user.id,
        text=comment_data.text,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.get(
    '/{task_id}/comments',
    response_model=list[CommentResponse],
    summary='Получить комментарии задачи.',
)
async def get_comments(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список комментариев к указанной задаче.
    
    Доступ к комментариям имеют только участники команды,
    к которой относится задача.
    """
    task = await db.scalar(
        select(Task)
        .join(TeamUser, Task.team_id == TeamUser.team_id)
        .where(
            Task.id == task_id,
            TeamUser.user_id == user.id,
        )
    )
    if not task:
        raise NotFoundItemExeption('Задача не найдена')
    comments = await db.scalars(
        select(Comment).where(
            Comment.task_id == task_id,
        )
    )

    return comments


@router.post(
    '/{task_id}/evaluation',
    response_model=EvaluationResponse,
    summary='Оценить выполненную задачу.',
)
async def task_evaluation(
    task_id: int,
    evaluation_data: EvaluationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Оценить выполненную задачу.
    
    Оценку может выставить только менеджер команды,
    к которой относится задача.
    
    Оценить можно только задачу со статусом DONE.
    Для одной задачи может быть создана только одна оценка.
    """
    task = await db.scalar(
        select(Task).where(Task.id == task_id)
    )
    if not task:
        raise NotFoundItemExeption('Задача не найдена')
    if task.status != TaskStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Нельзя оцениварь невыполненые задчи',
        )
    current_manager = await db.scalar(
        select(TeamUser)
        .join(Role, TeamUser.role_id == Role.id)
        .join(Team, TeamUser.team_id == Team.id)
        .where(
            Role.name == 'manager',
            Team.id == task.team_id,
            TeamUser.user_id == user.id,
        )
    )
    if not current_manager:
        raise PermissionDeniedExeption(
            'Оченку может постаивть только менеджер команды'
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


@router.get(
    '/{task_id}/evaluation',
    response_model=EvaluationResponse | None,
    summary='Получить оценку задачи.',
)
async def get_evaluation(
    task_id: int,
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить оценку указанной задачи.
    
    Доступ к оценке имеют только участники команды,
    к которой относится задача.
    
    Если для задачи ещё не создана оценка, возвращается null.
    """
    task = await db.scalar(
        select(Task)
        .join(TeamUser, Task.team_id == TeamUser.team_id)
        .where(
            Task.id == task_id,
            TeamUser.user_id == user_id,
        )
    )
    if not task:
        raise NotFoundItemExeption('Задача не найдена')
    evaluation = await db.scalar(
        select(Evaluation).where(
            Evaluation.task_id == task_id
        )
    )
    return evaluation 


@router.get(
    '/evaluations/me',
    response_model=list[EvaluationResponse],
    summary='Получить свои оценки.',
)
async def get_all_evaluation_me(
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить все оценки задач текущего пользователя.
    
    В ответ возвращается список оценок, выставленных задачам,
    исполнителем которых является текущий пользователь.
    """
    evaluation = await db.scalars(
        select(Evaluation).where(
            Evaluation.user_id == user_id
        )
    )
    if not evaluation:
        return []
    return evaluation
