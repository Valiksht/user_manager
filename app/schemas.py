from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models import TaskStatus
from app.utils import normalize_datetime


class UserCreate(BaseModel):
    """
    Данные для регистрации нового пользователя.
    """

    email: EmailStr
    username: str = Field(
        min_length=3,
        max_length=30,
        description='Уникальное имя пользователя.',
    )
    first_name: str = Field(
        min_length=3,
        max_length=30,
        description='Имя пользователя.',
    )
    last_name: str = Field(
        min_length=3,
        max_length=30,
        description='Фамилия пользователя.',
    )
    password: str = Field(
        min_length=3,
        max_length=30,
        description='Пароль пользователя.',
    )
    age: int | None = Field(
        default=None,
        le=100,
        description='Возраст пользователя.',
    )


class UserLogin(BaseModel):
    """
    Данные для авторизации пользователя.
    """

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """
    Данные пользователя, возвращаемые API.
    """

    id: int
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    age: int | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserSmallResponse(BaseModel):
    """
    Краткая информация о пользователе.
    Используется при отображении пользователей в связанных объектах.
    """

    id: int
    username: str
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """
    Данные авторизационного токена.
    """

    access_token: str
    token_type: str


class RoleInTeamResponse(BaseModel):
    """
    Роль пользователя внутри команды и список пользователей с этой ролью.
    """

    name: str
    description: str | None
    members: list[UserResponse]

    model_config = ConfigDict(from_attributes=True)


class TeamCreate(BaseModel):
    """
    Данные для создания новой команды.
    """

    name: str = Field(
        min_length=4,
        max_length=100,
        description='Название команды.',
    )
    description: str | None = Field(
        default=None,
        description='Описание команды.',
    )
    invite_code: str = Field(
        min_length=4,
        max_length=100,
        description='Код приглашения для вступления в команду.',
    )


class TeamUpdate(BaseModel):
    """
    Данные для изменения команды.
    """

    name: str | None = Field(
        default=None,
        description='Новое название команды.',
    )
    description: str | None = Field(
        default=None,
        description='Новое описание команды.',
    )
    invite_code: str | None = Field(
        default=None,
        description='Новый код приглашения.',
    )

    @model_validator(mode='before')
    @classmethod
    def validate_not_null(cls, data):
        if isinstance(data, dict):
            for field, value in data.items():
                if value is None:
                    raise ValueError(
                        f'Поле {field} не может быть null'
                    )
        return data


class TeamJoin(BaseModel):
    """
    Данные для вступления пользователя в команду.
    """

    invite_code: str = Field(
        min_length=4,
        max_length=100,
        description='Код приглашения команды.',
    )


class TeamResponseList(BaseModel):
    """
    Краткая информация о команде.
    """

    id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class TeamResponseDetail(BaseModel):
    """
    Подробная информация о команде с распределением участников по ролям.
    """

    id: int
    name: str
    description: str | None
    members: list[RoleInTeamResponse]

    model_config = ConfigDict(from_attributes=True)


class TeamJoinResponse(BaseModel):
    """
    Результат вступления пользователя в команду.
    """

    message: str
    team: str
    username: str
    role: str


class TeamRoleUpdate(BaseModel):
    """
    Данные для изменения роли пользователя в команде.
    """

    role_name: str


class TaskCreate(BaseModel):
    """
    Данные для создания новой задачи.
    """

    assignee_id: int = Field(
        description='ID пользователя, которому назначается задача.',
    )
    title: str = Field(
        max_length=200,
        description='Название задачи.',
    )
    description: str = Field(
        description='Описание задачи.',
    )
    due_date: date = Field(
        description='Срок выполнения задачи.',
    )


class TaskUpdate(BaseModel):
    """
    Данные для изменения существующей задачи.
    """

    title: str | None = Field(
        default=None,
        max_length=200,
        description='Новое название задачи.',
    )
    description: str | None = Field(
        default=None,
        description='Новое описание задачи.',
    )
    assignee_id: int | None = Field(
        default=None,
        description='ID нового исполнителя задачи.',
    )
    due_date: date | None = Field(
        default=None,
        description='Новый срок выполнения задачи.',
    )
    status: TaskStatus | None = Field(
        default=None,
        description='Новый статус задачи.',
    )

    @model_validator(mode='before')
    @classmethod
    def validate_not_null(cls, data):
        if isinstance(data, dict):
            for field, value in data.items():
                if value is None:
                    raise ValueError(
                        f'Поле {field} не может быть null'
                    )
        return data


class TaskResponse(BaseModel):
    """
    Данные задачи, возвращаемые API.
    """

    id: int
    team_id: int
    assignee_id: int | None = None
    title: str
    description: str | None = None
    status: str
    due_date: date | None = None

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    """
    Данные для создания комментария к задаче.
    """

    text: str = Field(
        description='Текст комментария.',
    )


class CommentResponse(BaseModel):
    """
    Данные комментария, возвращаемые API.
    """

    id: int
    task_id: int
    author_id: int
    text: str
    created_at: datetime


class EvaluationCreate(BaseModel):
    """
    Данные для оценки выполненной задачи.
    """

    score: int = Field(
        ge=1,
        le=5,
        description='Оценка задачи от 1 до 5.',
    )
    comment: str | None = Field(
        default=None,
        description='Комментарий менеджера к оценке.',
    )


class EvaluationResponse(BaseModel):
    """
    Данные оценки задачи, возвращаемые API.
    """

    task_id: int
    user_id: int
    manager_id: int
    score: int
    comment: str | None

    model_config = ConfigDict(from_attributes=True)


class EvaluationSummaryResponse(BaseModel):
    """
    Данные оценки зачач, включая средний балл за выполнение задач.
    """
    summary: float
    count: int
    detail: list[EvaluationResponse]


class TaskDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    assignee_id: int | None
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None

    comments: list[CommentResponse]
    evaluation: EvaluationResponse | None


class MeetCreate(BaseModel):
    """
    Данные для создания встречи команды.
    """

    name: str = Field(
        description='Название встречи.',
    )
    description: str | None = Field(
        default=None,
        description='Описание встречи.',
    )
    starts_at: datetime = Field(
        description='Дата и время начала встречи.',
    )
    ends_at: datetime = Field(
        description='Дата и время окончания встречи.',
    )
    users: list[int] | None = Field(
        default=None,
        description=(
            'Список ID участников встречи. '
            'Если не указан, во встречу добавляются все участники команды.'
        ),
    )

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def normalize_date(cls, value: datetime | None):
        if value is None:
            return None
        return normalize_datetime(value)

class MeetUpdate(BaseModel):
    """
    Данные для изменения изформации о встрече команды.
    """

    name: str | None  = Field(
        default=None,
        description='Название встречи.',
    )
    description: str | None = Field(
        default=None,
        description='Описание встречи.',
    )
    starts_at: datetime | None  = Field(
        default=None,
        description='Дата и время начала встречи.',
    )
    ends_at: datetime | None  = Field(
        default=None,
        description='Дата и время окончания встречи.',
    )
    users_add: list[int] | None = Field(
        default=None,
        description=(
            'Добавить учасников. '
        ),
    )
    users_remove: list[int] | None = Field(
        default=None,
        description=(
            'удалить учасников. '
        ),
        )

    @model_validator(mode='before')
    @classmethod
    def validate_not_null(cls, data):
        if isinstance(data, dict):
            for field, value in data.items():
                if value is None:
                    raise ValueError(
                        f'Поле {field} не может быть null'
                    )
        return data

    @model_validator(mode='after')
    def validate_user_list(self):
        if self.users_add is not None and self.users_remove is not None:
            intersection = set(self.users_add) & set(self.users_remove)
            if intersection:
                raise ValueError(
                    'Нельзя одновременно добавлять и удалять одного участника'
                )    

        if self.users_add is not None:
            if len(self.users_add) != len(set(self.users_add)):
                raise ValueError(
                    'В списке добавляемых участников есть дубликаты'
                )    

        if self.users_remove is not None:
            if len(self.users_remove) != len(set(self.users_remove)):
                raise ValueError(
                    'В списке удаляемых участников есть дубликаты'
                )    

        return self

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def normalize_date(cls, value: datetime | None):
        if value is None:
            return None
        return normalize_datetime(value)

class MeetingFilter(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator('starts_at', 'ends_at')
    @classmethod
    def normalize_date(cls, value: datetime | None):
        if value is None:
            return None
        return normalize_datetime(value)


class MeetResponse(BaseModel):
    """
    Данные встречи, возвращаемые API.
    """

    id: int
    team_id: int
    organizer_id: int
    name: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    users: list[UserSmallResponse]

    model_config = ConfigDict(from_attributes=True)


class CalendarResponse(BaseModel):
    """
    Данные по встречам и задачам
    """

    tasks: list[TaskResponse]
    meetings: list[MeetResponse]

    model_config = ConfigDict(from_attributes=True)
