import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, SecretStr, EmailStr, constr
from sqlalchemy.exc import IntegrityError
from sqlmodel import select, and_

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.usage import get_user_usage
from core import security
from core.security import get_password_hash, verify_password
from core.settings import settings
from models.tables.follower import Follower
from models.tables.user import User
from models.token import Token
from models.usage import Usage
from models.user_info import UserInfo
from models.user_info_search import UserInfoSearch

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: EmailStr
    password: SecretStr
    # lowercase alphanumeric characters
    username: constr(pattern="^[a-z0-9]+$")


class LoginResponse(BaseModel):
    username: constr(pattern="^[a-z0-9]+$")
    token: Token
    user_id: uuid.UUID

@router.post("/create")
async def user_create(user_in: UserCreate, session: SessionDep) -> LoginResponse:
    # TODO: verify username & email not already in use
    # TODO: verify username only contain acceptable character (only ASCII? no space?)

    # Create user instance
    new_user = User(
        email=user_in.email,
        username=user_in.username,
        # the salt is included in the hash
        password_hash=get_password_hash(user_in.password.get_secret_value()),
    )
    # Add it to DB
    session.add(new_user)

    try:
        # commit change
        session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=401,
            detail="User already exists",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return LoginResponse(
        token=Token(
            access_token=security.create_access_token(
                user_id=new_user.id, expires_delta=access_token_expires
            )
        ),
        username=user_in.username,
        user_id=new_user.id,
    )

class UserLogin(BaseModel):
    username: str
    password: SecretStr


@router.post("/login")
async def login(user_in: UserLogin, session: SessionDep) -> LoginResponse:
    statement = select(User).where(User.username == user_in.username)
    user = session.exec(statement).first()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not verify_password(user_in.password.get_secret_value(), user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return LoginResponse(
        token=Token(
            access_token=security.create_access_token(
                user_id=user.id, expires_delta=access_token_expires
            )
        ),
        username=user_in.username,
        user_id=user.id,
    )


@router.get("/me")
async def me(current_user: CurrentUserDep) -> UserInfo:
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        avatar_asset_id=current_user.avatar_asset_id
    )


@router.get("/search")
async def search(
        pattern: Annotated[str | None, Query(max_length=50, min_length=3)],
        current_user: CurrentUserDep,
        session: SessionDep
) -> list[UserInfoSearch]:
    stmt = (
        select(User, Follower.status)
        # join Follower table
        .join(Follower, onclause=and_(Follower.from_user == current_user.id, Follower.to_user == User.id), isouter=True)
        # username like pattern provided
        .where(User.username.contains(pattern), User.id != current_user.id)
        .limit(10)
    )

    results = session.exec(stmt).all()

    return [
        UserInfoSearch(
            id=user.id,
            username=user.username,
            avatar_asset_id=user.avatar_asset_id,
            follow_status=status
        )
        for user, status in results
    ]


@router.get("/usage")
async def get_usage(current_user: CurrentUserDep, session: SessionDep) -> Usage:
    return get_user_usage(current_user, session)
