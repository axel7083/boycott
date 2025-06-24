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

    # if the asset is private
    if asset.author != current_user.id and asset.asset_visibility == AssetVisibility.PRIVATE:
        err = f"asset {asset_id} is private. current user {current_user.id} does not have permission to access asset authored by {asset.author} with visibility {asset.asset_visibility}."
        logger.info(err)
        # TODO: Handle permission
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err
        )

    return stream_resource(
        minio_client=minio_client,
        asset_hash=asset.asset_hash,
    )
