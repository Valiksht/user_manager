from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.role import get_curret_manager_by_task
from app.dependencies.task import get_task_obj_with_user_odj
from app.models import (
    Task,
    User,
)
from app.schemas import (
    CommentCreate,
    CommentResponse,
    EvaluationCreate,
    EvaluationResponse,
    TaskDetailResponse,
    TaskResponse,
)
from app.services.auth import (
    get_current_user,
    get_id_from_token,
)
from app.services.tasks import (
    create_task_comment,
    create_task_evaluation,
    get_task_comment_list,
    get_task_evaluation,
    get_user_evaluation_list,
    task_detail,
    task_for_user,
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
    return await task_for_user(user_id, db)


@router.get(
    '/{task_id}',
    response_model=TaskDetailResponse,
    summary='Получить данные о задаче.',
)
async def get_task_detail(
    task_id: int,
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить подробные данные о задаче,
    включая коментарии и оценку.
    """
    return await task_detail(task_id, user_id, db)


@router.post(
    '/{task_id}/comments',
    response_model=CommentResponse,
    summary='Добавить комментарий к задаче.',
)
async def task_comment(
    comment_data: CommentCreate,
    task: Task = Depends(get_task_obj_with_user_odj),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Добавить комментарий к указанной задаче.

    Добавлять комментарии могут только участники команды,
    к которой относится задача.
    Комментарий сохраняется с указанием автора.
    """
    return await create_task_comment(comment_data, task.id, user.id, db)


@router.get(
    '/{task_id}/comments',
    response_model=list[CommentResponse],
    summary='Получить комментарии задачи.',
)
async def get_comments(
    task: Task = Depends(get_task_obj_with_user_odj),
    user_id: User = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список комментариев к указанной задаче.

    Доступ к комментариям имеют только участники команды,
    к которой относится задача.
    """
    return await get_task_comment_list(task.id, db)


@router.post(
    '/{task_id}/evaluation',
    response_model=EvaluationResponse,
    summary='Оценить выполненную задачу.',
)
async def task_evaluation(
    evaluation_data: EvaluationCreate,
    task: Task = Depends(get_task_obj_with_user_odj),
    user: User = Depends(get_curret_manager_by_task),
    db: AsyncSession = Depends(get_db),
):
    """
    Оценить выполненную задачу.

    Оценку может выставить только менеджер команды,
    к которой относится задача.

    Оценить можно только задачу со статусом DONE.
    Для одной задачи может быть создана только одна оценка.
    """
    return await create_task_evaluation(evaluation_data, task, user, db)


@router.get(
    '/{task_id}/evaluation',
    response_model=EvaluationResponse | None,
    summary='Получить оценку задачи.',
)
async def get_evaluation(
    task: Task = Depends(get_task_obj_with_user_odj),
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить оценку указанной задачи.

    Доступ к оценке имеют только участники команды,
    к которой относится задача.

    Если для задачи ещё не создана оценка, возвращается null.
    """
    return await get_task_evaluation(task.id, db)


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
    return await get_user_evaluation_list(user_id, db)
