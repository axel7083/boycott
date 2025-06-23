import hashlib
from io import BytesIO

from PIL import UnidentifiedImageError, Image
from fastapi import UploadFile, HTTPException
from sqlmodel import Session
from starlette import status

from api.utils.usage import get_user_usage
from core.minio import minio_client
from core.settings import settings
from models.asset import Asset, AssetType
from models.user import User


async def upload_image_to_asset(
        image: UploadFile,
        current_user: User,
        session: Session
) -> Asset:
    if image.size is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image size is required."
        )

    if image.size > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Maximum size is 5MB."
        )

    usage = get_user_usage(current_user, session)
    if usage.asset_size_sum + image.size > usage.asset_size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Not enough space left"
        )

    # 1. Read uploaded content
    original_content = await image.read()

    # 2. Open the image and convert to PNG
    try:
        with Image.open(BytesIO(original_content)) as img:
            # Ensure it's a valid image
            img = img.convert("RGBA")  # Use RGBA to support transparency if needed
            png_buffer = BytesIO()
            img.save(png_buffer, format="PNG")
            png_buffer.seek(0)
            png_content = png_buffer.read()
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail="Unsupported or invalid image format"
        )

    # 3. Compute SHA256 of PNG content
    sha256_hash = hashlib.sha256(png_content).hexdigest()

    # 4. Store PNG in MinIO
    try:
        minio_client.put_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=sha256_hash,
            data=BytesIO(png_content),
            length=len(png_content),
            content_type="image/png"
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to store image"
        )

    # 5. Create the asset row
    return Asset(
        author=current_user.id,
        asset_hash=sha256_hash,
        asset_size=len(png_content),
        assert_type=AssetType.IMAGE,
    )
