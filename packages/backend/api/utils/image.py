import uuid

from fastapi import UploadFile, HTTPException
from minio.helpers import ObjectWriteResult
from sqlmodel import Session
from starlette import status

from api.utils.usage import get_user_usage
from core.minio import minio_client
from core.settings import settings
from models.tables.asset import Asset, AssetType, AssetVisibility
from models.tables.user import User

AUTHOR_METADATA_KEY = "author"

async def upload_image_to_asset(
        image: UploadFile,
        current_user: User,
        session: Session,
        visibility: AssetVisibility = AssetVisibility.PRIVATE,
) -> Asset:
    if image.size is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image size is required."
        )

    # 🔑 Assert content type from the request header
    if image.content_type != "image/jpeg":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {image.content_type}"
        )

    if image.size > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image too large. Maximum size is {settings.MAX_IMAGE_SIZE}."
        )

    usage = get_user_usage(current_user, session)
    if usage.asset_size_sum + image.size > usage.asset_size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Not enough space left"
        )

    # Generate a unique asset ID to use as object_name in MinIO
    asset_id = uuid.uuid4()

    try:
        # Stream directly to MinIO
        result: ObjectWriteResult = minio_client.put_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=str(asset_id),
            data=image.file,
            length=image.size,
            content_type=image.content_type,
            metadata={
                AUTHOR_METADATA_KEY: current_user.id,
            }
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to store image"
        )

    # 5. Create the asset row
    return Asset(
        id=asset_id,
        author=current_user.id,
        asset_etag=result.etag,
        asset_size=image.size,
        asset_type=AssetType.IMAGE_JPEG,
        asset_visibility=visibility,
    )
