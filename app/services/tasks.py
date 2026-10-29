from datetime import date, datetime, timezone

from fastapi import (
    HTTPException,
    status,
)

from app.crud.tasks import (
    create_comment,
    create_evaluation,
    create_task,
    get_comment_from_task_id,
    get_evaluation,
    get_task_id_with_user_in_team,
    get_task_list_user,
    get_task_with_details,
    get_user_evaluation_summary,
    update_comment,
)
from app.crud.tasks import (
    get_user_evaluation_list as evaluation_list,
)
from app.crud.tasks import (
    update_task as update_task_crud,
)
from app.crud.teams import (
    user_in_team,
)
from app.dependencies.role import get_manager_role
from app.models import (
    TaskStatus,
)
from app.schemas import EvaluationSummaryResponse
from app.services.handlers import (
    NotFoundItemException,
    PermissionDeniedException,
)


async def create_new_tast(task_data, team_id, user_id, db):
    exist_user = await user_in_team(team_id, user_id, db)
    if not exist_user:
        raise PermissionDeniedException(
            'Вы не состоите в данной команде'
        )
    manager_role = await get_manager_role(db)
    if exist_user.role_id != manager_role.id:
        raise PermissionDeniedException(
            'Вы не можете создавать задачи для этой команды'
        )
    current_team = await user_in_team(
        team_id, task_data.assignee_id, db
    )
    if not current_team:
        raise NotFoundItemException(
            'Назначаемый пользователь не состоит в этой команде'
        )
    if task_data.due_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Дата выполнения не может быть раньше текущей',
        )
    task = create_task(team_id, task_data, db)
    return task


async def update_task(task_data, team_id, user_id, task, db):
    exist_user = await user_in_team(team_id, user_id, db)
    if not exist_user:
        raise PermissionDeniedException(
            'Вы не состоите в данной команде'
        )
    manager_role = await get_manager_role(db)
    perission = exist_user.role_id == manager_role.id
    update_data = task_data.model_dump(exclude_unset=True)

    if not perission and task.assignee_id != user_id:
        raise PermissionDeniedException(
            'Вы не можете изменить эту задачу'
        )
    update_data = task_data.model_dump(exclude_unset=True)
    if not perission and not set(update_data).issubset({'status'}):
        raise PermissionDeniedException(
            'Вы можете изменить только статус задачи'
        )

    if 'assignee_id' in update_data and update_data['assignee_id']:
        current_team = await user_in_team(
            team_id, task_data.assignee_id, db
        )
        if not current_team:
            raise NotFoundItemException(
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

    task = await update_task(task, update_data, db)
    return task


async def task_detail(task_id, user_id, db):
    depends_user = await get_task_id_with_user_in_team(
        task_id, user_id, db
    )
    if not depends_user:
        raise PermissionDeniedException(
            'Вы не можете просматривать информацию об этой задаче'
        )
    task = await get_task_with_details(task_id, db)
    return task


async def task_for_user(user_id, db):
    task = await get_task_list_user(user_id, db)
    return task


async def create_task_comment(comment_data, task_id, user_id, db):
    comment = create_comment(task_id, user_id, comment_data, db)
    return comment


async def update_task_comment(comment_data, comment, user_id, db):
    if comment.author_id != user_id:
        raise PendingDeprecationWarning(
            'Вы не можете изменять чужие комментарии'
        )
    if comment.text == comment_data.text:
        return comment
    update_data = comment_data.model_dump(exclude_unset=True)
    update_data['created_at'] = datetime.now(timezone.utc)
    comment = await update_comment(update_data, comment, db)
    return comment


async def delete_comment(comment, user, db):
    if (
        comment.author_id != user.id
        or user.is_admin != True
        or user.is_superuser != True
    ):
        raise PermissionDeniedException(
            'Вы не можете удалить коментарий'
        )
    await db.delete(comment)
    await db.commit()


async def get_task_comment_list(task_id, db):
    comments = await get_comment_from_task_id(task_id, db)
    return comments


async def create_task_evaluation(evaluation_data, task, user, db):
    if task.status != TaskStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Нельзя оценивать невыполненные задачи',
        )
    evaluation = create_evaluation(evaluation_data, task, user, db)
    return evaluation


async def get_task_evaluation(task_id, db):
    evaluation = await get_evaluation(task_id, db)
    return evaluation


async def get_user_evaluation_list(user_id, db):
    evaluations = await evaluation_list(user_id, db)
    if not evaluations:
        return []
    count, summary = await get_user_evaluation_summary(user_id, db)
    return EvaluationSummaryResponse(
        summary=round(summary, 2) if summary is not None else 0.0,
        count = count,
        detail = evaluations,
    )
