from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from core.minio import minio_client
from core.settings import settings

router = APIRouter(prefix="/assets", tags=["assets"])

@router.get("/{sha256}")
async def get_image(
    sha256: str,
):
    try:
        # 2. Get the object from MinIO
        response = minio_client.get_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=sha256
        )

        # 3. Stream the content back to the client
        return StreamingResponse(
            response,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename={sha256}.png"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Image not found")
