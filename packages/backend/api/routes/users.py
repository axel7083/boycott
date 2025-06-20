from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, SecretStr
from sqlalchemy.exc import IntegrityError

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.usage import get_user_usage
from core import security
from core.security import get_password_hash, verify_password
from core.settings import settings
from models.user import User
from models.token import Token
from sqlmodel import select

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    email: str
    password: SecretStr
    username: str

@router.post("/create")
async def user_create(user_in: UserCreate, session: SessionDep):
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

    return new_user

class UserLogin(BaseModel):
    username: str
    password: SecretStr

@router.post("/login")
async def login(user_in: UserLogin, session: SessionDep):
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
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )

@router.get("/me")
async def me(current_user: CurrentUserDep):
    return {
        "username": current_user.username,
    }

@router.get("/search")
async def search(
        pattern: Annotated[str | None, Query(max_length=50, min_length=3)],
        current_user: CurrentUserDep,
        session: SessionDep
):
    # always limit to 10 results
    statement = select(User).where(User.username.contains(pattern)).limit(10)
    users = session.exec(statement).all()

    return [{
        "username": user.username,
        "user_id": user.id
    } for user in users if user.id != current_user.id]

@router.get("/usage")
async def get_usage(current_user: CurrentUserDep, session: SessionDep):
    return get_user_usage(current_user, session)