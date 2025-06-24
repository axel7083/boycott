import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from core.minio import minio_client
from core.settings import settings
from models.tables.asset import Asset, AssetVisibility

router = APIRouter(prefix="/assets", tags=["assets"])

@router.get("/{asset_id}")
async def get_image(
    asset_id: uuid.UUID,
    current_user: CurrentUserDep,
    session: SessionDep
):
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    # if the asset is private
    if asset.author != current_user.id and asset.asset_visibility == AssetVisibility.PRIVATE:
        # TODO: Handle permission
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Asset is private")

    try:
        # 2. Get the object from MinIO
        response = minio_client.get_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=asset.asset_hash,
        )

        # 3. Stream the content back to the client
        return StreamingResponse(
            response,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename={asset.asset_hash}.png"
            }
        )
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail="Image not found")
