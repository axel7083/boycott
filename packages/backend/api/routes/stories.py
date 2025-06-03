import hashlib
from io import BytesIO

from PIL import Image
from fastapi import APIRouter, HTTPException, UploadFile
from sqlmodel import select

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from core.minio import minio_client
from core.settings import settings
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
        raise HTTPException(status_code=404, detail="Image not found")

    return user_story

@router.post("/")
async def post_story(
        image: UploadFile,
        current_user: CurrentUserDep,
        session: SessionDep
):
    if image.content_type != "image/png":
        raise HTTPException(
            status_code=501,
            detail="only png image supported",
        )

    # Read the content into memory
    content = await image.read()

    # 2. Verify PNG image
    try:
        img = Image.open(BytesIO(content))
        if img.format != "PNG":
            raise HTTPException(
                status_code=400,
                detail="Invalid PNG image"
            )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format"
        )

    # 3. Compute SHA256
    sha256_hash = hashlib.sha256(content).hexdigest()

    # 4. Store in MinIO
    try:
        minio_client.put_object(
            bucket_name=settings.IMAGES_BUCKET,
            object_name=sha256_hash,
            data=BytesIO(content),
            length=len(content),
            content_type="image/png"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to store image"
        )

    user_story = Story(
        author=current_user.id,
        asset_hash=sha256_hash,
    )
    session.add(user_story)
    session.commit()

    # 5. Return the SHA256
    return {"sha256": sha256_hash}