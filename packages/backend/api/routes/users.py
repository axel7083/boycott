from datetime import timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, SecretStr

from packages.backend.api.dependencies.current_user import CurrentUserDep
from packages.backend.api.dependencies.session import SessionDep
from packages.backend.core import security
from packages.backend.core.security import get_password_hash, verify_password
from packages.backend.core.settings import settings
from packages.backend.models import User, Token
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
    # commit change
    session.commit()
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