import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile
from pydantic import BaseModel, SecretStr, EmailStr, constr
from sqlalchemy.exc import IntegrityError
from starlette import status
from starlette.responses import StreamingResponse

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.image import upload_image_to_asset
from api.utils.minio import stream_resource
from api.utils.usage import get_user_usage
from core import security
from core.minio import minio_client
from core.security import get_password_hash, verify_password
from core.settings import settings
from models.sucess_response import SuccessResponse
from models.tables.asset import Asset
from models.tables.user import User
from models.token import Token
from sqlmodel import select

from models.usage import Usage
from models.user_info import UserInfo
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
) -> list[UserInfo]:
    # always limit to 10 results
    statement = select(User).where(User.username.contains(pattern)).limit(10)
    users = session.exec(statement).all()

    return [
        UserInfo(
            id=user.id,
            username=user.username,
            avatar_asset_id=user.avatar_asset_id
        ) for user in users if user.id != current_user.id
    ]

@router.get("/usage")
async def get_usage(current_user: CurrentUserDep, session: SessionDep) -> Usage:
    return get_user_usage(current_user, session)

@router.post("/avatar")
async def set_avatar(
        image: UploadFile,
        current_user: CurrentUserDep,
        session: SessionDep
) -> SuccessResponse:
    asset = await upload_image_to_asset(
        image=image,
        current_user=current_user,
        session=session
    )

    session.add(asset)
    current_user.avatar_asset_id = asset.id
    session.add(current_user)

    session.commit()

    return SuccessResponse()

@router.delete("/avatar")
async def delete_avatar(
        current_user: CurrentUserDep,
        session: SessionDep
) -> SuccessResponse:
    statement = select(User, Asset).where(
        User.id == current_user.id,
        Asset.id == User.avatar_asset_id,
    )

    results = session.exec(statement).first()
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found",
        )

    user, asset = results

    # Delete corresponding object in storage
    minio_client.remove_object(
        bucket_name=settings.IMAGES_BUCKET,
        object_name=asset.asset_hash,
    )
    # update user
    user.avatar_asset_id = None
    session.add(user)
    # delete asset row
    session.delete(asset)
    # commit
    session.commit()

    return SuccessResponse()

@router.get("/avatar/{user_id}")
async def get_avatar(
        user_id: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep
) -> StreamingResponse:
    # TODO: ensure blocked user cannot access data
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    statement = select(User, Asset).where(
        User.id == user_id,
        Asset.id == User.avatar_asset_id,
    )

    results = session.exec(statement).first()
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found",
        )

    _, asset = results

    return stream_resource(
        minio_client=minio_client,
        asset_hash=asset.asset_hash,
    )