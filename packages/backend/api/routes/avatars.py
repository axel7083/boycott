import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from sqlmodel import select
from starlette import status
from starlette.responses import StreamingResponse

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.image import upload_image_to_asset
from api.utils.minio import stream_resource
from core.minio import minio_client
from core.settings import settings
from models.sucess_response import SuccessResponse
from models.tables.asset import Asset
from models.tables.user import User

router = APIRouter(prefix="/avatars", tags=["avatars"])


@router.post("/avatar")
async def set_avatar(
        image: UploadFile,
        current_user: CurrentUserDep,
        session: SessionDep
) -> SuccessResponse:
    # Upload new asset to minio
    asset = await upload_image_to_asset(
        image=image,
        current_user=current_user,
        session=session
    )

    # Delete any existing assets first
    old_avatar_asset: Asset | None = None
    if current_user.avatar_asset_id is not None:
        # Get corresponding asset
        old_avatar_asset = session.get(Asset, current_user.avatar_asset_id)

        # Delete corresponding object in storage
        minio_client.remove_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=old_avatar_asset.asset_hash,
        )

    session.add(asset)
    current_user.avatar_asset_id = asset.id
    session.add(current_user)

    # Delete the asset
    if old_avatar_asset:
        session.delete(old_avatar_asset)

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