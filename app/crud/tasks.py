from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Comment, Evaluation, Task, TeamUser
from app.services.hendlers import NotFoundItemExeption


async def get_task_with_team_id(task_id, team_id, db):
    task = await db.scalar(
        select(Task).where(
            Task.id == task_id, Task.team_id == team_id
        )
    )
    if not task:
        raise NotFoundItemExeption('Задача не найдена')
    return task

async def get_task_list_user(user_id, db):
    tasks = await db.scalars(
        select(Task).where(
            Task.assignee_id == user_id
        )
    )
    return tasks

async def get_task_obj_with_user_in_team(task_id, user_id, db):
    task = await db.scalar(
        select(Task)
        .join(TeamUser, Task.team_id == TeamUser.team_id)
        .where(
            Task.id == task_id, TeamUser.user_id == user_id
        )
    )
    return task

async def get_task_id_with_user_in_team(task_id, user_id, db):
    task = await db.scalar(
        select(Task.id)
        .join(TeamUser, Task.team_id == TeamUser.team_id)
        .where(
            Task.id == task_id, TeamUser.user_id == user_id
        )
    )
    return task

async def get_task_with_details(
        task_id, db
):
    task_detail = await db.scalar(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.comments),
            selectinload(Task.evaluation),
        )
    )
    return task_detail

async def get_comment_from_task_id(task_id, db):
    comments = await db.scalars(
        select(Comment).where(
            Comment.task_id == task_id,
        )
    )
    return comments

async def get_evaluation(task_id, db):
    evaluation = await db.scalar(
        select(Evaluation).where(
            Evaluation.task_id == task_id
        )
    )
    return evaluation

async def get_user_evaluation_list(user_id, db):
    evaluations = await db.scalars(
        select(Evaluation).where(
            Evaluation.user_id == user_id
        )
    )
    return evaluations