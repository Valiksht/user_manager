from app.services.auth import create_jwt_token


async def test_create_task_comment(
    create_task,
    create_jwt,
    client,
):
    comment_data = {
        'text': 'Мой комментарий к задаче',
    }

    response = await client.post(
        f'/tasks/{create_task.id}/comments',
        json=comment_data,
        headers={
            'Authorization': (
                f"Bearer {create_jwt['token']['access_token']}"
            ),
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data['task_id'] == create_task.id
    assert response_data['author_id'] == create_jwt['user'].id
    assert response_data['text'] == comment_data['text']

async def test_create_comment_for_foreign_task(
    create_task,
    create_users_not_in_team,
    client,
):
    token = create_jwt_token(create_users_not_in_team.id)
    comment_data = {
        'text': 'Чужой комментарий',
    }

    response = await client.post(
        f'/tasks/{create_task.id}/comments',
        json=comment_data,
        headers={
            'Authorization': (
                f"Bearer {token['access_token']}"
            ),
        },
    )

    assert response.status_code == 404

async def test_get_task_comments(
    create_task,
    create_comment,
    create_jwt,
    client,
):
    response = await client.get(
        f'/tasks/{create_task.id}/comments',
        headers={
            'Authorization': (
                f"Bearer {create_jwt['token']['access_token']}"
            ),
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert len(response_data) == 1

    assert response_data[0]['task_id'] == create_task.id
    assert response_data[0]['author_id'] == create_jwt['user'].id
    assert response_data[0]['text'] == 'Тестовый комментарий'

async def test_get_comments_for_foreign_task(
    create_task,
    create_bad_jwt,
    client,
):
    response = await client.get(
        f'/tasks/{create_task.id}/comments',
        headers={
            'Authorization': (
                f"Bearer {create_bad_jwt['token']['access_token']}"
            ),
        },
    )

    assert response.status_code == 200