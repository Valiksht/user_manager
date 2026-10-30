from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models import Comment, Evaluation, Task, TeamUser
from app.services.handlers import NotFoundItemException


async def get_task_with_team_id(task_id, team_id, db):
    task = await db.scalar(
        select(Task).where(Task.id == task_id, Task.team_id == team_id)
    )
    if not task:
        raise NotFoundItemException('Задача не найдена')
    return task


async def get_task_list_user(user_id, db):
    tasks = await db.scalars(
        select(Task).where(Task.assignee_id == user_id)
    )
    return tasks


async def get_task_list_user_with_date(
    user_id,
    db,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
):
    query = select(Task).where(Task.assignee_id == user_id)
    if starts_at is not None:
        query = query.where(Task.due_date >= starts_at.date())
    if ends_at is not None:
        query = query.where(Task.due_date <= ends_at.date())
    tasks = await db.scalars(query)
    return tasks


async def get_task_obj_with_user_in_team(task_id, user_id, db):
    task = await db.scalar(
        select(Task)
        .join(TeamUser, Task.team_id == TeamUser.team_id)
        .where(Task.id == task_id, TeamUser.user_id == user_id)
    )
    return task


async def get_task_id_with_user_in_team(task_id, user_id, db):
    task = await db.scalar(
        select(Task.id)
        .join(TeamUser, Task.team_id == TeamUser.team_id)
        .where(Task.id == task_id, TeamUser.user_id == user_id)
    )
    return task


async def get_task_with_details(task_id, db):
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

async def get_comment_by_id(comment_id, task_id, db):
    comment = await db.scalar(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.task_id == task_id
        )
    )
    return comment

async def get_evaluation(task_id, db):
    evaluation = await db.scalar(
        select(Evaluation).where(Evaluation.task_id == task_id)
    )
    return evaluation

async def get_user_evaluation_summary(user_id, db):
    count, summary = (
        await db.execute(
            select(
                func.count(Evaluation.id),
                func.avg(Evaluation.score),
            ).where(
                Evaluation.user_id == user_id,
            )
        )
    ).first()
    return count, summary

async def get_user_evaluation_list(user_id, db):
    evaluations = await db.scalars(
        select(Evaluation).where(Evaluation.user_id == user_id)
    )
    return evaluations

async def create_task(team_id, task_data, db):
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

async def update_task(task, update_data, db):
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task

async def create_comment(task_id, user_id, comment_data, db):
    comment = Comment(
        task_id=task_id,
        author_id=user_id,
        text=comment_data.text,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment

async def update_comment(comment_data, comment_obj, db):
    for field, value in comment_data.items():
        setattr(comment_obj, field, value)
    await db.commit()
    await db.refresh(comment_obj)
    return comment_obj

async def create_evaluation(evaluation_data, task, user, db):
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

async def update_evaluation():
    pass