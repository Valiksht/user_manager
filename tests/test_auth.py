from sqlalchemy import select

from app.models import User
from app.services.auth import get_id_from_token

# test_invalid_token


async def test_register_success(user_data, client, db):
    response = await client.post(
        '/auth/register',
        json=user_data[0],
    )
    assert response.status_code == 201
    data = response.json()
    assert data['email'] == 'test@test.ru'
    assert data['username'] == 'testuser'
    assert data['first_name'] == 'Test'
    assert data['last_name'] == 'User'
    assert data['age'] == 25
    assert 'password' not in data
    user = await db.scalar(
        select(User).where(User.email == 'test@test.ru')
    )
    assert user is not None
    assert user.username == 'testuser'


async def test_register_duplicate_email(
    user_data, client, db
):
    response = await client.post(
        '/auth/register',
        json=user_data[0],
    )
    assert response.status_code == 201
    dub_email = user_data[1].copy()
    dub_email['email'] = user_data[0]['email']
    response = await client.post(
        '/auth/register',
        json=dub_email,
    )
    assert response.status_code == 400


async def test_register_duplicate_username(
    user_data, client
):
    response = await client.post(
        '/auth/register',
        json=user_data[0],
    )
    assert response.status_code == 201
    dub_username = user_data[1].copy()
    dub_username['username'] = user_data[0]['username']
    response = await client.post(
        '/auth/register',
        json=dub_username,
    )
    assert response.status_code == 400


async def test_login_success(user_data, client):
    response_register = await client.post(
        '/auth/register',
        json=user_data[0],
    )
    assert response_register.status_code == 201
    response_login = await client.post(
        '/auth/login',
        json=user_data[0],
    )
    data = response_login.json()
    assert response_login.status_code == 200
    assert 'access_token' in data
    assert data['token_type'] == 'Bearer'
    assert data['access_token']


async def test_login_wrong_password(user_data, client):
    response_register = await client.post(
        '/auth/register',
        json=user_data[0],
    )
    assert response_register.status_code == 201
    user_wrong_password = user_data[0].copy()
    user_wrong_password['password'] = user_data[1]['password']
    response_login = await client.post(
        '/auth/login',
        json=user_wrong_password,
    )
    assert response_login.status_code == 401
    assert response_login.json().get('detail') == 'Неверный email или пароль'

async def test_invalid_token(user_data, client):
    response_register = await client.post(
        '/auth/register',
        json=user_data[0],
    )
    assert response_register.status_code == 201
    response_login = await client.post(
        '/auth/login',
        json=user_data[0],
    )
    data = response_login.json()
    assert response_login.status_code == 200
    assert data['token_type'] == 'Bearer'
    assert data['access_token']
    current_user_id = await get_id_from_token(data['access_token'])
    assert current_user_id == response_register.json()['id']
