from fastapi import APIRouter, HTTPException, UploadFile
from sqlmodel import select
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.image import upload_image_to_asset
from core.minio import minio_client
from core.settings import settings
from models.sucess_response import SuccessResponse
from models.tables.asset import Asset
from models.tables.story import Story

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
    asset = session.get(Asset, user_story.asset_id)
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
        object_name=asset.asset_hash,
    )

    return SuccessResponse()

@router.post("/")
async def post_story(
        image: UploadFile,
        current_user: CurrentUserDep,
        session: SessionDep
):
    asset = await upload_image_to_asset(
        image=image,
        current_user=current_user,
        session=session
    )

    # 6. Create story row
    user_story = Story(
        author=current_user.id,
        asset_id=asset.id,
    )
    session.add(asset)
    session.add(user_story)
    session.commit()

    return {"sha256": asset.asset_hash}