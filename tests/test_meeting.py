import pytest


async def test_create_meet(
    create_team,
    get_super_user_token,
    meet_data,
    client,
):
    response = await client.post(
        f'/calendar/{create_team.id}',
        json=meet_data,
        headers={
            'Authorization': (
                f'Bearer '
                f'{get_super_user_token["token"]["access_token"]}'
            ),
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data['name'] == meet_data['name']
    assert (
        response_data['description']
        == meet_data['description']
    )
    assert response_data['team_id'] == create_team.id
    assert (
        response_data['organizer_id']
        == get_super_user_token['user'].id
    )


async def test_create_meet_by_member(
    create_team_with_users,
    create_jwt,
    meet_data,
    client,
):
    meet_url = (
        f'/calendar/{create_team_with_users["team_obj"].id}'
    )
    response = await client.post(
        meet_url,
        json=meet_data,
        headers={
            'Authorization': (
                f'Bearer {create_jwt["token"]["access_token"]}'
            ),
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    'starts_at, ends_at, expected_detail',
    [
        (
            '2026-10-01T10:00:00',
            '2026-10-01T09:00:00',
            'Время окончания должно быть позже времени начала',
        ),
        (
            '2020-01-01T10:00:00',
            '2020-01-01T11:00:00',
            'Время начала должно быть позже текущего времени',
        ),
    ],
)
async def test_create_meet_invalid_dates(
    create_team,
    get_super_user_token,
    meet_data,
    client,
    starts_at,
    ends_at,
    expected_detail,
):
    meet_data['starts_at'] = starts_at
    meet_data['ends_at'] = ends_at
    response = await client.post(
        f'/calendar/{create_team.id}',
        json=meet_data,
        headers={
            'Authorization': (
                f'Bearer {get_super_user_token["token"]["access_token"]}'
            ),
        },
    )
    assert response.status_code == 400
    assert response.json()['detail'] == expected_detail


async def test_create_overlapping_meet(
    create_team,
    create_meeting,
    get_super_user_token,
    meet_data,
    client,
):
    meet_data['starts_at'] = (
        create_meeting.starts_at.isoformat()
    )
    meet_data['ends_at'] = (
        create_meeting.ends_at.isoformat()
    )
    response = await client.post(
        f'/calendar/{create_team.id}',
        json=meet_data,
        headers={
            'Authorization': (
                f'Bearer '
                f'{get_super_user_token["token"]["access_token"]}'
            ),
        },
    )
    assert response.status_code == 409
    assert (
        response.json()['detail']
        == 'Время встречи пересекается с существующей встречей'
    )


async def test_create_meet_with_selected_users(
    create_team_with_users,
    get_super_user_token,
    create_users,
    meet_data,
    client,
):
    meet_url = (
        f'/calendar/{create_team_with_users["team_obj"].id}'
    )
    meet_data['users'] = [
        create_users[0].id,
        create_users[1].id,
    ]
    response = await client.post(
        meet_url,
        json=meet_data,
        headers={
            'Authorization': (
                f'Bearer '
                f'{get_super_user_token["token"]["access_token"]}'
            ),
        },
    )
    assert response.status_code == 200
    response_data = response.json()
    user_ids = {
        user['id'] for user in response_data['users']
    }
    assert user_ids == {
        create_users[0].id,
        create_users[1].id,
    }


async def test_get_calendar(
    create_user_meeting,
    create_jwt,
    client,
):
    response = await client.get(
        '/calendar',
        headers={
            'Authorization': (
                f'Bearer {create_jwt["token"]["access_token"]}'
            ),
        },
    )
    assert response.status_code == 200
    response_data = response.json()

    assert len(response_data) == 1
    assert response_data[0]['id'] == create_user_meeting.id
    assert (
        response_data[0]['name'] == create_user_meeting.name
    )


async def test_get_calendar_starts_at_filter(
    create_meeting,
    create_jwt,
    client,
):
    response = await client.get(
        '/calendar',
        params={
            'starts_at': '2026-10-02T00:00:00',
        },
        headers={
            'Authorization': (
                f'Bearer {create_jwt["token"]["access_token"]}'
            ),
        },
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_get_my_meetings(
    create_user_meeting,
    create_jwt,
    client,
):
    response = await client.get(
        '/calendar/me',
        headers={
            'Authorization': (
                f'Bearer {create_jwt["token"]["access_token"]}'
            ),
        },
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]['id'] == create_user_meeting.id
