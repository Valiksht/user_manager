from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Role, Team, TeamUser, User
from app.services.handlers import NotFoundItemException


async def get_role(role_name, db):
    if not role_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='не передан "role_name"',
        )
    role = await db.scalar(select(Role).where(Role.name == role_name))
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Не инициализированны базовые роли команды',
        )
    return role


async def get_all_role_name(db):
    roles = await db.scalars(select(Role.name))
    return roles


async def get_team_by_name(team_name, db) -> Team:
    if not team_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Не передан "team_name"',
        )
    team = await db.scalar(select(Team).where(Team.name == team_name))
    return team


async def get_team_members(team_id, db):
    team_members = await db.scalars(
        select(TeamUser)
        .where(TeamUser.team_id == team_id)
        .options(
            selectinload(TeamUser.user),
            selectinload(TeamUser.role),
        )
    )
    return team_members


async def user_in_team(team_id, user_id, db):
    exist_user = await db.scalar(
        select(TeamUser).where(
            TeamUser.user_id == user_id,
            TeamUser.team_id == team_id,
        )
    )
    return exist_user


async def get_team_with_user(user_id, db):
    teams = await db.scalars(
        select(Team)
        .join(TeamUser)
        .where(TeamUser.user_id == user_id)
        .options(
            selectinload(Team.members).selectinload(TeamUser.user),
            selectinload(Team.members).selectinload(TeamUser.role),
        )
    )
    return teams


async def get_user_in_team(team_id, db):
    users = await db.scalars(
        select(User)
        .join(TeamUser, User.id == TeamUser.user_id)
        .where(TeamUser.team_id == team_id)
    )
    return users


async def create_team(
    team_data, user_creater, invite_code_hash, manager_role, db
):
    team = Team(
        name=team_data.name,
        description=team_data.description,
        invite_code=invite_code_hash,
    )
    db.add(team)
    await db.flush()
    team_user = TeamUser(
        user_id=user_creater.id,
        team_id=team.id,
        role_id=manager_role.id,
    )
    db.add(team_user)
    await db.commit()
    await db.refresh(team)
    return team


async def update_team(team_obj, update_data, db):
    for field, value in update_data.items():
        setattr(team_obj, field, value)
    await db commit()
    await db.refresh(team_obj)
    return team_obj