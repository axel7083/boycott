import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.logger import LoggerDep
from api.dependencies.session import SessionDep
from api.utils.minio import stream_resource
from core.minio import minio_client
from models.tables.asset import Asset, AssetVisibility
from models.tables.follower import Follower, FollowStatus

router = APIRouter(prefix="/assets", tags=["assets"])

@router.get("/{asset_id}")
async def get_image(
    asset_id: uuid.UUID,
    current_user: CurrentUserDep,
    session: SessionDep,
    logger: LoggerDep,
) -> StreamingResponse:
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # if the asset is public - let's shortcut and stream
    if asset.asset_visibility == AssetVisibility.PUBLIC:
        return stream_resource(
            minio_client=minio_client,
            asset_hash=asset.asset_hash,
        )

    # if the current user is the asset's author - let's shortcut and stream
    if asset.author == current_user.id:
        return stream_resource(
            minio_client=minio_client,
            asset_hash=asset.asset_hash,
        )

    # if the current user is an approved follower of asset#author
    follow = session.get(Follower, (current_user.id, asset.author))
    if follow is not None and follow.status == FollowStatus.APPROVED:
        return stream_resource(
            minio_client=minio_client,
            asset_hash=asset.asset_hash,
        )

    err = f"asset {asset_id} is private. current user {current_user.id} is not an approved follower of {asset.author}."
    logger.info(err)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="private asset"
    )
