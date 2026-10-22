from sqlalchemy import select

from app.models import User


async def test_me_url(user_data, client):
    response_register = await client.post(
        '/auth/register',
        json=user_data[0],
    )
    assert response_register.status_code == 201
    response_login = await client.post(
        '/auth/login',
        json=user_data[0],
    )
    token_data = response_login.json()
    response_me = await client.get(
        '/users/me',
        headers={
            'Authorization': f'Bearer {token_data["access_token"]}',
        },
    )
    me_data = response_me.json()
    assert response_register.json()['id'] == me_data['id']
    assert response_me.status_code == 200
    assert me_data['username'] == user_data[0].get(
        'username'
    )
    assert 'password' not in me_data


async def test_get_all_users(
    create_users, create_jwt, client
):
    token = create_jwt['token']['access_token']
    response_register = await client.get(
        '/users',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response_register.status_code == 200
    assert len(create_users) == len(
        response_register.json()
    )


async def test_make_admin_success(
    client,
    get_super_user_token,
    create_users,
    db,
):
    token = get_super_user_token['token']['access_token']
    user = create_users[0]
    response = await client.post(
        f'/users/{user.id}/admin',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert response.status_code == 201
    data = response.json()
    assert data['id'] == user.id
    assert data['email'] == user.email
    assert data['is_active'] is True
    assert data.get('is_admin') is None
    user_from_db = await db.scalar(
        select(User).where(User.id == user.id)
    )
    assert user_from_db.is_admin == True



async def test_make_admin_forbidden_for_regular_user(
    client,
    create_jwt,
):
    token = create_jwt['token']['access_token']

    response = await client.post(
        f'/users/{create_jwt["user"].id}/admin',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 403
    assert response.json()['detail'] == (
        'Операция доступна только пользователю с правами superuser'
    )



async def test_make_admin_user_not_found(
    client,
    get_super_user_token,
):
    token = get_super_user_token['token']['access_token']

    response = await client.post(
        '/users/999999/admin',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 404
    assert response.json()['detail'] == (
        'Пользователь с id 999999 не найден'
    )
