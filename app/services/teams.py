from fastapi import (
    HTTPException,
    status,
)

from app.crud.teams import (
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
from app.services.hendlers import (
    NotFoundItemExeption,
    PermissionDeniedExeption,
)


async def create_new_team(
    team_data, user_creater, manager_role, db    
):
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
    return team

async def join_to_team_with_invite_code(user_data, team, user, role, db):
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

def transform_team_user_respose(team_members):
    roles = {}
    for member in team_members: #TODO Немного переделать
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

async def team_detail(team, user_id, db):
    team_members = await get_team_members(team.id, db)
    members = team_members.all()
    if not any(member.user_id == user_id for member in members):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Вас нес среди участников команды',
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
            detail='Вас нес среди участников команды',
        )
    team_in_role = transform_team_user_respose(members)
    return team_in_role

async def remove_member(team_id, user_id, current_user, db):
    exist_user = await user_in_team(team_id, current_user.id, db)
    if not exist_user:
        raise PermissionDeniedExeption(
            'Вы не состоите в данной команде'
        )
    manager_role = await get_manager_role(db)
    if exist_user.role_id != manager_role.id:
        raise PermissionDeniedExeption(
            'Только менеджер может удалять участников'
        )

    member_in_team = await user_in_team(team_id, user_id, db)
    if not member_in_team:
        raise NotFoundItemExeption(
            'Пользователь не состоит в этой команде'
        )
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Менеджер не может удалить себя из команды',
        )
    await db.delete(member_in_team)
    await db.commit()
    # messege = f'Пользователь {user_id} удален из конмады'
    # return {'messege': messege}


