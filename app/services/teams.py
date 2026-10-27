from fastapi import (
    HTTPException,
    status,
)

from app.crud.teams import (
    get_all_role_name,
    get_role,
    get_team_by_id,
    get_team_by_name,
    get_team_members,
    get_team_with_user,
    user_in_team,
)
from app.dependencies.role import get_manager_role
from app.models import Team, TeamUser
from app.schemas import (
    RoleInTeamResponse,
    TeamJoinResponse,
    TeamResponseDetail,
    UserResponse,
)
from app.services.auth import (
    hash_password,
    verify_password,
)
from app.services.handlers import (
    NotFoundItemException,
    PermissionDeniedException,
)


def transform_team_user_respose(team_members):
    roles = {}
    for member in team_members:
        role_name = member.role.name
        role_description = member.role.description

        if role_name not in roles:
            roles[role_name] = {
                'description': role_description,
                'users': [],
            }

        roles[role_name]['users'].append(
            UserResponse.model_validate(member.user)
        )
    return [
        RoleInTeamResponse(
            name=role_name,
            description=data['description'],
            members=data['users'],
        )
        for role_name, data in roles.items()
    ]


async def create_new_team(team_data, user_creater, manager_role, db):
    exist_team = await get_team_by_name(team_data.name, db)
    if exist_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Команда с таким названием уже существует',
        )
    team = Team(
        name=team_data.name,
        description=team_data.description,
        invite_code=hash_password(team_data.invite_code),
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
    return TeamResponseDetail(
        id=team.id,
        name=team.name,
        description=team.description,
        members=[
            RoleInTeamResponse(
                name=manager_role.name,
                description=manager_role.description,
                members=[UserResponse.model_validate(user_creater)],
            )
        ],
    )


async def update_team(team_id, team_data, manager_role, user, db):
    team = await get_team_by_id(team_id, db)
    if team_data.name is not None:
        exist_team = await get_team_by_name(team_data.name, db)
        if exist_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Команда с таким названием уже существует',
            )
        team.name = team_data.name
    if team_data.description is not None:
        team.description = team_data.description
    if team_data.invite_code is not None:
        team.invite_code = hash_password(team_data.invite_code)
    await db.commit()
    await db.refresh(team)
    team_members = await get_team_members(team.id, db)
    members = team_members.all()
    team_in_role = transform_team_user_respose(members)
    return TeamResponseDetail(
        id=team.id,
        name=team.name,
        description=team.description,
        members=team_in_role,
    )


async def update_role_in_team(role_data, team_id, user, db):
    team_user = await user_in_team(team_id, user.id, db)
    if team_user is None:
        raise NotFoundItemException(
            f'Пользователь {user.username} не состоит в команде'
        )
    new_role = await get_role(role_data.role_name, db)
    if new_role is None:
        roles = await get_all_role_name(db)
        raise NotFoundItemException(
            f'Роль с именем {role_data.role_name} не найдена.'
            f'Список доступных ролей: {roles.all()}.'
        )
    if new_role.id == team_user.role_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Данная роль уже присвоена пользователю',
        )
    team_user.role_id = new_role.id
    await db.commit()
    await db.refresh(team_user)
    return RoleInTeamResponse(
        name=new_role.name,
        description=new_role.description,
        members=[user],
    )


async def join_to_team_with_invite_code(
    user_data, team, user, role, db
):
    invite_code_is_valid = verify_password(
        user_data.invite_code, team.invite_code
    )
    if not invite_code_is_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Неверный invite код',
        )
    exist_user = await user_in_team(team.id, user.id, db)
    if exist_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Вы уже находитесь в этой команде',
        )
    user_join = TeamUser(
        user_id=user.id,
        team_id=team.id,
        role_id=role.id,
    )
    db.add(user_join)
    await db.commit()
    await db.refresh(user_join)
    return TeamJoinResponse(
        message='Пользователь вступил в команду',
        username=user.username,
        team=team.name,
        role=role.name,
    )


async def teams_with_user(user_id, db):
    teams = await get_team_with_user(user_id, db)
    return teams.all()


async def team_detail(team, user_id, db):
    team_members = await get_team_members(team.id, db)
    members = team_members.all()
    if not any(member.user_id == user_id for member in members):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Вас нет среди участников команды',
        )
    team_in_role = transform_team_user_respose(members)
    return TeamResponseDetail(
        id=team.id,
        name=team.name,
        description=team.description,
        members=team_in_role,
    )


async def team_detail_members(team, user_id, db):
    team_members = await get_team_members(team.id, db)
    members = team_members.all()
    if not any(member.user_id == user_id for member in members):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Вас нет среди участников команды',
        )
    team_in_role = transform_team_user_respose(members)
    return team_in_role


async def remove_member(team_id, user_id, current_user, db):
    exist_user = await user_in_team(team_id, current_user.id, db)
    if not exist_user:
        raise PermissionDeniedException(
            'Вы не состоите в данной команде'
        )
    manager_role = await get_manager_role(db)
    if exist_user.role_id != manager_role.id:
        raise PermissionDeniedException(
            'Только менеджер может удалять участников'
        )

    member_in_team = await user_in_team(team_id, user_id, db)
    if not member_in_team:
        raise NotFoundItemException(
            'Пользователь не состоит в этой команде'
        )
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Менеджер не может удалить себя из команды',
        )
    await db.delete(member_in_team)
    await db.commit()
