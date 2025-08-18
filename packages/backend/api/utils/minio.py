from fastapi import HTTPException
from minio import Minio
from minio.error import S3Error
from starlette import status
from starlette.responses import StreamingResponse

from core.settings import settings
from models.tables.asset import Asset, AssetType


def get_extension(asset_type: AssetType) -> str:
    match asset_type:
        case AssetType.IMAGE_JPEG:
            return "jpg"
        case _:
            raise ValueError(f"Unsupported asset type: {asset_type}")


def stream_resource(
        minio_client: Minio,
        asset: Asset,
) -> StreamingResponse:
    try:
        # 1. Get the object from MinIO
        response = minio_client.get_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=str(asset.id),
        )

        # 2. Stream the content back to the client
        return StreamingResponse(
            response,
            media_type=asset.asset_type.value, # enum string value
            headers={
                "Content-Disposition": f"inline; filename={asset.id}.{get_extension(asset.asset_type)}",
                "ETag": asset.asset_etag,
            }
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )


def try_delete_asset(minio_client: Minio, asset_hash: str) -> None:
    try:
        # Delete corresponding object in storage
        minio_client.remove_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=asset_hash,
        )
    except S3Error as e:
        print(f"Error deleting object: {e}")
