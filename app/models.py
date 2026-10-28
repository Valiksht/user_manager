from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )
    age: Mapped[int | None] = mapped_column(nullable=True)

    team_memberships: Mapped[list['TeamUser']] = relationship(
        back_populates='user'
    )
    assigned_tasks: Mapped[list['Task']] = relationship(
        back_populates='assignee',
        foreign_keys='Task.assignee_id',
    )
    meetings: Mapped[list['UserMeeting']] = relationship(
        back_populates='user'
    )
    organized_meetings: Mapped[list['Meeting']] = relationship(
        back_populates='organizer',
        foreign_keys='Meeting.organizer_id',
    )
    comments: Mapped[list['Comment']] = relationship(
        back_populates='author'
    )
    evaluations: Mapped[list['Evaluation']] = relationship(
        back_populates='user',
        foreign_keys='Evaluation.user_id',
    )
    given_evaluations: Mapped[list['Evaluation']] = relationship(
        back_populates='manager',
        foreign_keys='Evaluation.manager_id',
    )


class Team(Base):
    __tablename__ = 'teams'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    invite_code: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    members: Mapped[list['TeamUser']] = relationship(
        back_populates='team'
    )
    tasks: Mapped[list['Task']] = relationship(back_populates='team')
    meetings: Mapped[list['Meeting']] = relationship(
        back_populates='team'
    )


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    members: Mapped[list['TeamUser']] = relationship(
        back_populates='role'
    )


class TeamUser(Base):
    __tablename__ = 'team_users'
    __table_args__ = (
        UniqueConstraint('user_id', 'team_id', name='uq_tema_user'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey('teams.id'), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey('roles.id'), nullable=False
    )

    user: Mapped['User'] = relationship(
        back_populates='team_memberships'
    )
    team: Mapped['Team'] = relationship(back_populates='members')
    role: Mapped['Role'] = relationship(back_populates='members')


class TaskStatus(str, Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    DONE = 'done'


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey('teams.id'), nullable=False
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey('users.id'), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        default=TaskStatus.OPEN, nullable=False
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    team: Mapped['Team'] = relationship(back_populates='tasks')
    assignee: Mapped['User | None'] = relationship(
        back_populates='assigned_tasks',
        foreign_keys=[assignee_id],
    )
    comments: Mapped[list['Comment']] = relationship(
        back_populates='task'
    )
    evaluation: Mapped['Evaluation | None'] = relationship(
        back_populates='task'
    )


class Comment(Base):
    __tablename__ = 'comments'

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey('tasks.id'), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now().replace(microsecond=0),
        nullable=False,
    )

    task: Mapped['Task'] = relationship(back_populates='comments')
    author: Mapped['User'] = relationship(back_populates='comments')


class Meeting(Base):
    __tablename__ = 'meetings'

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey('teams.id'), nullable=False
    )
    organizer_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    team: Mapped['Team'] = relationship(back_populates='meetings')
    organizer: Mapped['User'] = relationship(
        back_populates='organized_meetings',
        foreign_keys=[organizer_id],
    )
    participants: Mapped[list['UserMeeting']] = relationship(
        back_populates='meeting'
    )


class UserMeeting(Base):
    __tablename__ = 'user_meetings'
    __table_args__ = (
        UniqueConstraint(
            'user_id', 'meeting_id', name='uq_user_meeting'
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), nullable=False
    )
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey('meetings.id'), nullable=False
    )

    user: Mapped['User'] = relationship(back_populates='meetings')
    meeting: Mapped['Meeting'] = relationship(
        back_populates='participants'
    )


class Evaluation(Base):
    __tablename__ = 'evaluations'

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey('tasks.id'), nullable=False, unique=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), nullable=False
    )
    manager_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'), nullable=False
    )
    score: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now().replace(microsecond=0),
        nullable=False,
    )

    task: Mapped['Task'] = relationship(back_populates='evaluation')
    user: Mapped['User'] = relationship(
        back_populates='evaluations', foreign_keys=[user_id]
    )
    manager: Mapped['User'] = relationship(
        back_populates='given_evaluations',
        foreign_keys=[manager_id],
    )
