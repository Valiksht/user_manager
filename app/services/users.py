from app.crud.users import get_user_deteil as user_deteil
from app.crud.users import get_user_list as user_list
from app.models import User
from app.services.auth import (
    create_jwt_token,
    hash_password,
)


async def create_user(user_data, db):
    user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        password_hash=hash_password(user_data.password),
        age=user_data.age,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

def get_token(user):
    return create_jwt_token(user.id)

async def get_user_deteil(user_id, db):
    return await user_deteil(user_id, db)

async def get_user_list(db):
    return await user_list(db)

async def update_user_from_admin(user, db):
    user.is_admin = True
    await db.commit()
    await db.refresh(user)
    return user
