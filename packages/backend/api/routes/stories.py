import hashlib
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, HTTPException, UploadFile
from sqlmodel import select
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.usage import get_user_usage
from core.minio import minio_client
from core.settings import settings
from models.asset import Asset, AssetType
from models.story import Story

router = APIRouter(prefix="/stories", tags=["stories"])

@router.get("/")
async def get_stories(
        current_user: CurrentUserDep,
        session: SessionDep
):
    statement = select(Story).where(Story.author == current_user.id)
    results = session.exec(statement)
    return results.all()

@router.get("/{story_id}")
async def get_story(
    story_id: str,
    current_user: CurrentUserDep,
    session: SessionDep
):
    user_story = session.get(Story, story_id)
    if user_story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    return user_story

@router.delete("/{story_id}")
async def delete_story(
        story_id: str,
        current_user: CurrentUserDep,
        session: SessionDep
):
    user_story = session.get(Story, story_id)
    if user_story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )

    if user_story.author != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to delete this story"
        )

    session.delete(user_story)
    session.commit()

    # Delete corresponding object in storage
    minio_client.remove_object(
        bucket_name=settings.IMAGES_BUCKET,
        object_name=user_story.asset_hash,
    )

    return {"success": True}

@router.post("/")
async def post_story(
        image: UploadFile,
        current_user: CurrentUserDep,
        session: SessionDep
):
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
    asset = Asset(
        asset_hash=sha256_hash,
        asset_size=len(png_content),
        assert_type=AssetType.IMAGE,
    )

    # 6. Create story row
    user_story = Story(
        author=current_user.id,
        asset_id=asset.id,
    )
    session.add(asset)
    session.add(user_story)
    session.commit()

    return {"sha256": sha256_hash}