from pydantic import ValidationError
import pytest
from datetime import datetime, timedelta

from app.schemas import MeetUpdate
from tests.conftest import get_future_date


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
            get_future_date(10).isoformat(),
            get_future_date(9).isoformat(),
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
        == 'Время встречи пересекается с существующей встречей в команде'
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
        get_super_user_token['user'].id,
    }

async def test_create_meet_with_users_not_in_team(
    create_team_with_users,
    get_super_user_token,
    create_users_not_in_team,
    meet_data,
    client,
):
    meet_url = (
        f'/calendar/{create_team_with_users["team_obj"].id}'
    )
    meet_data['users'] = [
        create_users_not_in_team.id,
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
    assert response.status_code == 404


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

    assert len(response_data['meetings']) == 1
    assert response_data['meetings'][0]['id'] == create_user_meeting.id
    assert (
        response_data['meetings'][0]['name'] == create_user_meeting.name
    )
    assert response_data['tasks'] == []


async def test_get_calendar_starts_at_filter(
    create_meeting,
    create_jwt,
    client,
):
    response = await client.get(
        '/calendar',
        params={
            'starts_at': (datetime.now()+timedelta(days=3)).isoformat(),
        },
        headers={
            'Authorization': (
                f'Bearer {create_jwt["token"]["access_token"]}'
            ),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        'tasks': [],
        'meetings': [],
    }


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
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    assert response_data[0]['id'] == create_user_meeting.id

async def test_create_meet_with_users_in_one_time(
    create_user_meeting,
    create_second_team_with_users,
    get_super_user_token,
    meet_data,
    client,
):
    response = await client.post(
        f'/calendar/{create_second_team_with_users['team_obj'].id}',
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
            == 'Время встречи пересекается с существующей встречей учасника встречи'
        )

def test_meet_update_normalizes_naive_datetimes():
    data = MeetUpdate(starts_at="2030-01-01T10:00:00")

    assert data.starts_at.tzinfo is not None
    assert data.starts_at.utcoffset().total_seconds() == 0


def test_meet_update_rejects_user_in_add_and_remove_lists():
    with pytest.raises(ValidationError):
        MeetUpdate(users_add=[1, 2], users_remove=[2, 3])


def test_meet_update_rejects_duplicate_user_ids():
    with pytest.raises(ValidationError):
        MeetUpdate(users_add=[1, 1])


async def test_create_meeting_rejects_duration_over_eight_hours(
    create_team,
    get_super_user_token,
    meet_data,
    client,
):
    starts_at = get_future_date(8)
    ends_at = starts_at + timedelta(hours=9)
    meet_data["starts_at"] = starts_at.isoformat()
    meet_data["ends_at"] = ends_at.isoformat()

    response = await client.post(
        f"/calendar/{create_team.id}",
        headers={
            "Authorization": (
                f"Bearer {get_super_user_token['token']['access_token']}"
            ),
        },
        json=meet_data,
    )

    assert response.status_code == 400
