import pytest

from app.schemas import TaskResponse
from app.services.auth import create_jwt_token
from tests.conftest import get_future_date


async def test_create_task(
    create_team_with_users,
    task_data,
    get_super_user_token,
    client,
):
    task_data['due_date'] = task_data[
        'due_date'
    ].isoformat()
    response_url = f'/teams/{create_team_with_users["team_obj"].id}/tasks'
    response_task = await client.post(
        response_url,
        headers={
            'Authorization': f'Bearer {get_super_user_token["token"]["access_token"]}',
        },
        json=task_data,
    )
    assert response_task.status_code == 201
    response_data = response_task.json()
    assert (
        response_data['team_id']
        == create_team_with_users['team_obj'].id
    )
    assert (
        response_data['assignee_id']
        == task_data['assignee_id']
    )
    assert (
        response_data['description']
        == task_data['description']
    )
    assert response_data['status'] == 'open'
    assert (
        response_data['due_date'] == task_data['due_date']
    )


@pytest.mark.parametrize(
    'field, new_value, role, should_change',
    [
        ('title', 'Новое название', 'manager', True),
        ('description', 'Новое описание', 'manager', True),
        ('assignee_id', 2, 'manager', True),
        ('due_date', get_future_date().isoformat(), 'manager', True),
        ('status', 'done', 'manager', True),
        ('title', 'Новое название', 'assignee', False),
        (
            'description',
            'Новое описание',
            'assignee',
            False,
        ),
        ('assignee_id', 2, 'assignee', False),
        ('due_date', get_future_date().isoformat(), 'assignee', False),
        ('status', 'done', 'assignee', True),
    ],
)
async def test_update_task(
    create_task,
    create_jwt,
    get_super_user_token,
    client,
    db,
    field,
    new_value,
    role,
    should_change,
):
    if role == 'manager':
        token = get_super_user_token['token'][
            'access_token'
        ]
    else:
        token = create_jwt['token']['access_token']
    old_value = getattr(create_task, field)
    response = await client.patch(
        f'/teams/{create_task.team_id}/tasks/{create_task.id}',
        headers={
            'Authorization': f'Bearer {token}',
        },
        json={
            field: new_value,
        },
    )
    if should_change:
        assert response.status_code == 200
        response_data = response.json()
        if field == 'due_date':
            assert response_data[field] == new_value

            await db.refresh(create_task)
            assert (
                create_task.due_date.isoformat()
                == new_value
            )

        elif field == 'status':
            assert response_data[field] == new_value.lower()

            await db.refresh(create_task)
            assert (
                create_task.status.value
                == new_value.lower()
            )

        else:
            assert response_data[field] == new_value

            await db.refresh(create_task)
            assert getattr(create_task, field) == new_value
    else:
        assert response.status_code == 403
        await db.refresh(create_task)
        assert getattr(create_task, field) == old_value


@pytest.mark.parametrize(
    'current_user, len_task',
    [
        (True, 1),
        (False, 0),
    ],
)
async def test_get_all_task(
    create_task,
    create_jwt,
    create_bad_jwt,
    client,
    current_user,
    len_task,
):
    if current_user:
        token = create_jwt['token']['access_token']
    else:
        token = create_bad_jwt['token']['access_token']
    response = await client.get(
        '/tasks',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == len_task
    if response_data:
        assert (
            response_data[0]['assignee_id']
            == create_jwt['user'].id
        )




async def test_get_task_detail_success(
    create_task,
    create_comment,
    create_jwt,
    client,
):
    response = await client.get(
        f'/tasks/{create_task.id}',
        headers={
            'Authorization': (
                f'Bearer {create_jwt["token"]["access_token"]}'
            ),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == create_task.id
    assert data['title'] == create_task.title
    assert len(data['comments']) == 1
    assert data['comments'][0]['text'] == create_comment.text
    assert data['evaluation'] is None


async def test_get_task_detail_user_not_in_team(
    create_task,
    create_users_not_in_team,
    client,
):
    token = create_jwt_token(create_users_not_in_team.id)
    response = await client.get(
        f'/tasks/{create_task.id}',
        headers={
            'Authorization': f'Bearer {token["access_token"]}',
        },
    )
    assert response.status_code == 403


async def test_get_task_detail_task_not_found(
    create_jwt,
    client,
):
    response = await client.get(
        '/tasks/999999',
        headers={
            'Authorization': (
                f'Bearer {create_jwt["token"]["access_token"]}'
            ),
        },
    )
    assert response.status_code == 404


async def test_get_task_detail_unauthorized(
    create_task,
    client,
):
    response = await client.get(f'/tasks/{create_task.id}')
    assert response.status_code == 401

@pytest.mark.parametrize(
    "field",
    ["title", "description", "assignee_id", "due_date", "status"],
)
async def test_task_patch_rejects_null(
    create_task,
    get_super_user_token,
    client,
    field,
):
    """PATCH не должен принимать null вместо значения поля задачи."""
    response = await client.patch(
        f"/teams/{create_task.team_id}/tasks/{create_task.id}",
        headers={
            "Authorization": (
                f"Bearer {get_super_user_token['token']['access_token']}"
            ),
        },
        json={field: None},
    )

    assert response.status_code == 422

async def test_task_patch_rejects_unknown_status(
    create_task,
    get_super_user_token,
    client,
):
    response = await client.patch(
        f"/teams/{create_task.team_id}/tasks/{create_task.id}",
        headers={
            "Authorization": (
                f"Bearer {get_super_user_token['token']['access_token']}"
            ),
        },
        json={"status": "unknown_status"},
    )

    assert response.status_code == 422


def test_task_response_accepts_nullable_model_fields():
    """Схема ответа должна соответствовать nullable-полям модели Task."""
    response = TaskResponse.model_validate(
        {
            "id": 1,
            "team_id": 1,
            "assignee_id": None,
            "title": "Задача",
            "description": None,
            "status": "open",
            "due_date": None,
        }
    )

    assert response.description is None
    assert response.assignee_id is None
    assert response.due_date is None
