from sqlalchemy import distinct, func, select

from app.models import TeamUser


async def test_create_team(
    team_data, get_super_user_token, client
):
    response_register = await client.post(
        '/teams',
        headers={
            'Authorization': f'Bearer {get_super_user_token["token"]["access_token"]}',
        },
        json=team_data,
    )
    response_data = response_register.json()
    assert response_register.status_code == 201
    assert response_data['name'] == team_data['name']
    assert (
        response_data['description']
        == team_data['description']
    )
    assert 'invite_code' not in response_data
    assert len(response_data['members']) == 1
    members = response_data['members'][0]
    assert members['name'] == 'manager'
    assert len(members['members']) == 1
    assert (
        members['members'][0]['username']
        == get_super_user_token['user'].username
    )


async def test_join_to_team(
    create_team, team_data, create_jwt, client, db
):
    response_url = f'/teams/{create_team.id}/join'
    response_join = await client.post(
        response_url,
        headers={
            'Authorization': f'Bearer {create_jwt["token"]["access_token"]}',
        },
        json={'invite_code': team_data['invite_code']},
    )
    join_data = response_join.json()
    assert response_join.status_code == 201
    assert join_data['team'] == team_data['name']
    assert (
        join_data['username'] == create_jwt['user'].username
    )
    assert join_data['role'] == 'member'
    assert 'invite_code' not in join_data


async def test_get_member_team(
    create_team_with_users, create_jwt, client, db
):
    response_url = f'/teams/{create_team_with_users["team_obj"].id}/members'
    response_team_user = await client.get(
        response_url,
        headers={
            'Authorization': f'Bearer {create_jwt["token"]["access_token"]}',
        },
    )
    team_members_data = response_team_user.json()
    assert response_team_user.status_code == 200
    role_count = await db.scalar(
        select(
            func.count(func.distinct(TeamUser.role_id))
        ).where(
            TeamUser.team_id
            == create_team_with_users['team_obj'].id
        )
    )
    assert len(team_members_data) == role_count
    for role in team_members_data:
        if role['name'] == 'manager':
            assert len(role['members']) == 1
        elif role['name'] == 'member':
            assert len(role['members']) == len(
                create_team_with_users['team_user']
            )


async def test_get_team_detail(
    create_team_with_users, team_data, create_jwt, client
):
    response_url = (
        f'/teams/{create_team_with_users["team_obj"].id}'
    )
    response_join = await client.get(
        response_url,
        headers={
            'Authorization': f'Bearer {create_jwt["token"]["access_token"]}',
        },
    )
    assert response_join.status_code == 200
    response_data = response_join.json()
    assert (
        response_data['id']
        == create_team_with_users['team_obj'].id
    )
    assert (
        response_data['name']
        == create_team_with_users['team_obj'].name
    )
    assert (
        response_data['description']
        == create_team_with_users['team_obj'].description
    )
    assert 'invite_code' not in response_data


async def test_remove_team_member_success(
    client,
    get_super_user_token,
    create_team_with_users,
    db,
):
    token = get_super_user_token['token']['access_token']
    team_obj = create_team_with_users['team_obj']
    user_for_delete = create_team_with_users['team_user'][0]
    response = await client.delete(
        f'/teams/{team_obj.id}/members/{user_for_delete.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 204
    member = await db.scalar(
        select(TeamUser).where(
            TeamUser.team_id == team_obj.id,
            TeamUser.user_id == user_for_delete.id,
        )
    )
    assert member is None

async def test_remove_team_member_forbidden_for_member(
    client,
    create_jwt,
    create_team_with_users,
):
    token = create_jwt['token']['access_token']
    team_obj = create_team_with_users['team_obj']
    response = await client.delete(
        f'/teams/{team_obj.id}/members/{create_jwt['user'].id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 403
    assert response.json()['detail'] == (
        'Только менеджер может удалять участников'
    )

async def test_remove_team_member_not_found(
    client,
    get_super_user_token,
    create_team_with_users,
):
    token = get_super_user_token['token']['access_token']
    team_obj = create_team_with_users['team_obj']
    response = await client.delete(
        f'/teams/{team_obj.id}/members/999999',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 404
    assert response.json()['detail'] == (
        'Пользователь не состоит в этой команде'
    )

async def test_manager_cannot_remove_self(
    client,
    get_super_user_token,
    create_team_with_users,
):
    token = get_super_user_token['token']['access_token']
    team_obj = create_team_with_users['team_obj']
    response = await client.delete(
        f'/teams/{team_obj.id}/members/{get_super_user_token['user'].id}',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 400
    assert response.json()['detail'] == (
        'Менеджер не может удалить себя из команды'
    )

async def test_update_team_returns_all_members_and_200(
    create_team_with_users,
    get_super_user_token,
    client,
):
    team = create_team_with_users["team_obj"]
    response = await client.patch(
        f"/teams/{team.id}",
        headers={
            "Authorization": (
                f"Bearer {get_super_user_token['token']['access_token']}"
            ),
        },
        json={"name": "Обновлённая команда"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Обновлённая команда"

    total_members = sum(
        len(role["members"]) for role in data["members"]
    )
    # В команде один менеджер и все пользователи из create_users.
    assert total_members == len(create_team_with_users["team_user"]) + 1


async def test_updated_invite_code_can_be_used_to_join(
    create_team,
    create_jwt,
    get_super_user_token,
    client,
):
    team = create_team
    manager_token = get_super_user_token["token"]["access_token"]
    member_token = create_jwt["token"]["access_token"]

    update_response = await client.patch(
        f"/teams/{team.id}",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={"invite_code": "новый-код-приглашения"},
    )
    assert update_response.status_code == 200

    join_response = await client.post(
        f"/teams/{team.id}/join",
        headers={"Authorization": f"Bearer {member_token}"},
        json={"invite_code": "новый-код-приглашения"},
    )

    assert join_response.status_code == 201
    assert join_response.json()["role"] == "member"


async def test_update_role_returns_404_for_unknown_role(
    create_team_with_users,
    get_super_user_token,
    create_users,
    client,
):
    team = create_team_with_users["team_obj"]
    target_user = create_users[0]

    response = await client.patch(
        f"/teams/{team.id}/members/{target_user.id}",
        headers={
            "Authorization": (
                f"Bearer {get_super_user_token['token']['access_token']}"
            ),
        },
        json={"role_name": "role_that_does_not_exist"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]


async def test_invalid_bearer_token_returns_401(client):
    response = await client.get(
        "/users/me",
        headers={"Authorization": "Bearer definitely-not-a-valid-token"},
    )

    assert response.status_code == 401
