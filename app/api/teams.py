from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.role import (
    get_current_manager_by_team,
    get_manager_role,
    get_member_role,
)
from app.dependencies.task import get_task_obj_with_team_id
from app.dependencies.team import get_team_obj
from app.dependencies.users import get_user_obj_by_id
from app.models import Role, Task, Team, User
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
    TeamRoleUpdate,
    TeamUpdate,
    UserResponse,
)
from app.services.auth import (
    get_current_admin,
    get_current_user,
    get_id_from_token,
)
from app.services.tasks import create_new_tast, update_task
from app.services.teams import (
    create_new_team,
    join_to_team_with_invite_code,
    remove_member,
    team_detail,
    team_detail_members,
    teams_with_user,
    update_role_in_team,
    update_team,
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
    manager_role: Role = Depends(get_manager_role),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую команду.

    Операция доступна только пользователю с правами администратора.
    Создатель команды автоматически добавляется в неё с ролью manager.

    Название команды должно быть уникальным.

    Операция ограничена правом администратора, что бы ограничить
    создание команд обычными пользователями.
    """
    team = await create_new_team(team_data, user, manager_role, db)
    return team


@router.patch(
    '/{team_id}',
    response_model=TeamResponseDetail,
    status_code=status.HTTP_201_CREATED,
    summary='Изменить информацию о команде.',
)
async def team_update(   
    team_data: TeamUpdate,
    team_obj: Team = Depends(get_team_obj),
    user: User = Depends(get_current_admin),
    manager_role: Role = Depends(get_manager_role),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить информацию об указанной команде.

    Операция доступна только пользователю с правами администратора.

    Данные команды обновляются в соответствии с переданными значениями.
    """
    team = await update_team(team_obj, team_data, db)
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
    user_data: TeamJoin,
    team: Team = Depends(get_team_obj),
    user: User = Depends(get_current_user),
    member_role: Role = Depends(get_member_role),
    db: AsyncSession = Depends(get_db),
):
    """
    Добавить текущего пользователя в указанную команду.

    Для вступления необходимо передать корректный invite code команды.
    После вступления пользователю назначается роль member.

    Пользователь не может повторно вступить в команду, в которой уже состоит.
    """
    return await join_to_team_with_invite_code(
        user_data, team, user, member_role, db
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
    return await teams_with_user(user_id, db)


@router.get(
    '/{team_id}',
    response_model=TeamResponseDetail,
    summary='Получить информацию о команде.',
)
async def detail_team(
    team: Team = Depends(get_team_obj),
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить подробную информацию об указанной команде.

    Доступ к информации имеют только пользователи, состоящие в этой команде.
    В ответе возвращается информация о команде и её участниках,
    сгруппированных по ролям.
    """
    return await team_detail(team, user_id, db)


@router.get(
    '/{team_id}/members',
    response_model=list[RoleInTeamResponse],
    summary='Получить участников команды.',
)
async def team_members(
    team: Team = Depends(get_team_obj),
    user_id: int = Depends(get_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список участников указанной команды.

    Доступ к списку имеют только участники этой команды.
    Пользователи в ответе сгруппированы по назначенным им ролям.
    """
    return await team_detail_members(team, user_id, db)


@router.patch(
    '/{team_id}/members/{user_id}',
    response_model=RoleInTeamResponse,
    summary='Изменить роль.',
)
async def update_role(
    role_data: TeamRoleUpdate,
    team_id: int,
    user: User = Depends(get_user_obj_by_id),
    manager_user: User = Depends(get_current_manager_by_team),
    db: AsyncSession = Depends(get_db),
):
    """
    Изменить роль участника команды.

    Менеджер команды может изменить роль указанного участника.
    Пользователь, которому назначается роль, должен состоять в команде.
    """
    return await update_role_in_team(role_data, team_id, user, db)


@router.post(
    '/{team_id}/tasks',
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Создать задачу для команды.',
)
async def create_tasks(
    task_data: TaskCreate,
    team: Team = Depends(get_team_obj),
    user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую задачу и назначить её участнику команды.

    Создавать задачи может только менеджер указанной команды.
    Назначаемый пользователь должен состоять в этой команде.

    Дата выполнения задачи не может быть раньше текущей даты.
    """
    return await create_new_tast(task_data, team.id, user.id, db)


@router.patch(
    '/{team_id}/tasks/{task_id}',
    response_model=TaskResponse,
    summary='Изменить задачу.',
)
async def update_tasks(
    task_data: TaskUpdate,
    team_id: int,
    task: Task = Depends(get_task_obj_with_team_id),
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
    return await update_task(task_data, team_id, user.id, task, db)


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
    return await remove_member(team_id, user_id, current_user, db)
