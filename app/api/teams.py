from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Role, Task, Team, TeamUser, User
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

router = APIRouter(prefix='/teams', tags=['Team'])


@router.post(
    '',
    response_model=TeamResponseDetail,
    status_code=status.HTTP_201_CREATED,
    summary='Создать команду.',
)
async def team_create(
    team_data: TeamCreate,
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую команду.

    Операция доступна только пользователю с правами администратора.
    Создатель команды автоматически добавляется в неё с ролью manager.

    Название команды должно быть уникальным.

    Операция ограницена правом администратора, что бы ограничить
    создание команд обычными пользователями.
    """
    exist_team = await db.scalar(
        select(Team).where(Team.name == team_data.name)
    )
    if exist_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Команда с таким названием уже существует',
        )
    manager_role = await db.scalar(
        select(Role).where(Role.name == 'manager')
    )
    if not manager_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Не инициализированны базовые роли команды',
        )
    team = Team(
        name=team_data.name,
        description=team_data.description,
        invite_code=hash_password(team_data.invite_code),
    )
    db.add(team)
    await db.flush()

    team_user = TeamUser(
        user_id=user.id,
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
                members=[UserResponse.model_validate(user)],
            )
        ],
    )


@router.post(
    '/{team_id}/join',
    response_model=TeamJoinResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Вступить в команду.',
)
async def join_to_team(
    team_id: int,
    user_data: TeamJoin,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Добавить текущего пользователя в указанную команду.

    Для вступления необходимо передать корректный invite code команды.
    После вступления пользователю назначается роль member.

    Пользователь не может повторно вступить в команду, в которой уже состоит.
    """
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id,
        )
    )
    if not team:
        raise NotFoundItemExeption('Команды не существует')
    invite_code_is_valid = verify_password(
        user_data.invite_code, team.invite_code
    )
    if not invite_code_is_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Неверный invite код',
        )
    exist_user = await db.scalar(
        select(TeamUser).where(
            TeamUser.user_id == user.id,
            TeamUser.team_id == team_id,
        )
    )
    if exist_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Вы уже находитесь в этой команде',
        )
    member_role = await db.scalar(
        select(Role).where(Role.name == 'member')
    )
    user_join = TeamUser(
        user_id=user.id,
        team_id=team_id,
        role_id=member_role.id,
    )
    db.add(user_join)
    await db.commit()
    await db.refresh(user_join)
    return TeamJoinResponse(
        message='Пользователь вступил в команду',
        username=user.username,
        team=team.name,
        role=member_role.name,
    )


@router.get(
    '',
    response_model=list[TeamResponseList],
    summary='Получить команды c пользователем.',
)
async def team_list(
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список команд, в которых состоит текущий пользователь.

    Для каждой команды возвращается информация о её участниках
    и их ролях.
    """
    teams = await db.scalars(
        select(Team)
        .join(TeamUser)
        .where(TeamUser.user_id == user_id)
        .options(
            selectinload(Team.members).selectinload(
                TeamUser.user
            ),
            selectinload(Team.members).selectinload(
                TeamUser.role
            ),
        )
    )
    return teams.all()


@router.get(
    '/{team_id}',
    response_model=TeamResponseDetail,
    summary='Получить информацию о команде.',
)
async def detail_team(
    team_id: int,
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить подробную информацию об указанной команде.
    
    Доступ к информации имеют только пользователи, состоящие в этой команде.
    В ответе возвращается информация о команде и её участниках,
    сгруппированных по ролям.
    """
    team = await db.scalar(
        select(Team)
        .join(TeamUser)
        .where(Team.id == team_id)
        .where(TeamUser.user_id == user_id)
        .options(
            selectinload(Team.members).selectinload(
                TeamUser.user
            ),
            selectinload(Team.members).selectinload(
                TeamUser.role
            ),
        )
    )
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Вас нес среди участников команды',
        )
    roles = {}
    for member in team.members:
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
    return TeamResponseDetail(
        id=team.id,
        name=team.name,
        description=team.description,
        members=[
            RoleInTeamResponse(
                name=role_name,
                description=data['description'],
                members=data['users'],
            )
            for role_name, data in roles.items()
        ],
    )


@router.get(
    '/{team_id}/members',
    response_model=list[RoleInTeamResponse],
    summary='Получить участников команды.',
)
async def team_members(
    team_id: int,
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список участников указанной команды.
    
    Доступ к списку имеют только участники этой команды.
    Пользователи в ответе сгруппированы по назначенным им ролям.
    """
    team_members = await db.scalars(
        select(TeamUser)
        .where(TeamUser.team_id == team_id)
        .options(
            selectinload(TeamUser.user),
            selectinload(TeamUser.role),
        )
    )
    members = team_members.all()
    if not members:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='команды не существует или в ней нет участников',
        )
    if not any(
        member.user_id == user_id for member in members
    ):
        raise PermissionDeniedExeption(
            'Вы не состоите в этой команде'
        )
    roles = {}
    for member in members:
        role_name = member.role.name

        if role_name not in roles:
            roles[role_name] = {
                'description': member.role.description,
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


@router.post(
    '/{team_id}/tasks',
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Создать задачу для команды.',
)
async def create_tasks(
    task_data: TaskCreate,
    team_id: int,
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую задачу и назначить её участнику команды.
    
    Создавать задачи может только менеджер указанной команды.
    Назначаемый пользователь должен состоять в этой команде.
    
    Дата выполнения задачи не может быть раньше текущей даты.
    """
    current_user = await db.scalar(
        select(TeamUser)
        .join(Role, TeamUser.role_id == Role.id)
        .where(
            TeamUser.user_id == user_id,
            TeamUser.team_id == team_id,
            Role.name == 'manager',
        )
    )
    if not current_user:
        raise PermissionDeniedExeption(
            'Вы не можете создавать задачи для этой команды'
        )
    current_team = await db.scalar(
        select(Team)
        .join(TeamUser)
        .where(
            Team.id == team_id,
            TeamUser.user_id == task_data.assignee_id,
        )
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
        team_id=current_team.id,
        assignee_id=task_data.assignee_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch(
    '/{team_id}/tasks/{task_id}',
    response_model=TaskResponse,
    summary='Изменить задачу.',
)
async def update_tasks(
    task_data: TaskUpdate,
    team_id: int,
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Изменить существующую задачу команды.
    
    Менеджер команды может изменять доступные поля задачи.
    Исполнитель задачи может изменять только её статус.
    
    Пользователь не может изменять задачи, которые не относятся к его команде
    или к которым у него нет необходимых прав.
    """
    task = await db.scalar(
        select(Task).where(
            Task.id == task_id, Task.team_id == team_id
        )
    )
    if not task:
        raise NotFoundItemExeption('Задача не найдена')
    perission = await db.scalar(
        select(TeamUser)
        .join(Role, TeamUser.role_id == Role.id)
        .where(
            TeamUser.user_id == user.id,
            TeamUser.team_id == task.team_id,
            Role.name == 'manager',
        )
    )
    if not perission and task.assignee_id != user.id:
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
    for field, value in update_data.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete(
    '/{team_id}/members/{user_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Удалить участника из команды.',
)
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить пользователя из указанной команды.
    
    Операция доступна только менеджеру команды.
    Менеджер не может удалить самого себя из команды.
    
    Если указанный пользователь не состоит в команде, возвращается ошибка.
    """
    manager = await db.scalar(
        select(TeamUser)
        .join(Role, TeamUser.role_id == Role.id)
        .where(
            TeamUser.team_id == team_id,
            TeamUser.user_id == current_user.id,
            Role.name == 'manager',
        )
    )
    if not manager:
        raise PermissionDeniedExeption(
            'Только менеджер может удалять участников'
        )
    member = await db.scalar(
        select(TeamUser).where(
            TeamUser.team_id == team_id,
            TeamUser.user_id == user_id,
        )
    )
    if not member:
        raise NotFoundItemExeption(
            'Пользователь не состоит в этой команде'
        )
    if member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Менеджер не может удалить себя из команды',
        )
    await db.delete(member)
    await db.commit()
