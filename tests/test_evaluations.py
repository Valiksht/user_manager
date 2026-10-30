async def test_create_task_evaluation(
    create_done_task,
    get_super_user_token,
    client,
):
    response = await client.post(
        f'/tasks/{create_done_task.id}/evaluation',
        json={
            'score': 5,
            'comment': 'Хорошо выполнено',
        },
        headers={
            'Authorization': (
                f"Bearer {get_super_user_token['token']['access_token']}"
            ),
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data['task_id'] == create_done_task.id
    assert response_data['user_id'] == create_done_task.assignee_id
    assert (
        response_data['manager_id']
        == get_super_user_token['user'].id
    )
    assert response_data['score'] == 5
    assert response_data['comment'] == 'Хорошо выполнено'

async def test_create_evaluation_for_not_done_task(
    create_task,
    get_super_user_token,
    client,
):
    response = await client.post(
        f'/tasks/{create_task.id}/evaluation',
        json={
            'score': 5,
            'comment': 'Оценка',
        },
        headers={
            'Authorization': (
                f"Bearer {get_super_user_token['token']['access_token']}"
            ),
        },
    )

    assert response.status_code == 409

async def test_create_evaluation_by_member(
    create_done_task,
    create_jwt,
    client,
):
    response = await client.post(
        f'/tasks/{create_done_task.id}/evaluation',
        json={
            'score': 5,
            'comment': 'Попытка оценки',
        },
        headers={
            'Authorization': (
                f"Bearer {create_jwt['token']['access_token']}"
            ),
        },
    )

    assert response.status_code == 403

async def test_evaluation_summary_is_empty_object_when_user_has_no_scores(
    create_jwt,
    client,
):
    response = await client.get(
        "/tasks/evaluations/me",
        headers={
            "Authorization": (
                f"Bearer {create_jwt['token']['access_token']}"
            ),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "summary": 0.0,
        "count": 0,
        "detail": [],
    }
