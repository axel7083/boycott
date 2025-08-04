import uuid
from typing import Annotated

from fastapi import APIRouter, UploadFile, Form, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import select
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.image import upload_image_to_asset
from api.utils.minio import try_delete_asset
from core.minio import minio_client
from core.settings import settings
from models.sucess_response import SuccessResponse
from models.tables.asset import Asset
from models.tables.follower import Follower, FollowStatus
from models.tables.plant import Plant
from models.tables.plant_update import PlantUpdate

router = APIRouter(prefix="/plants", tags=["plants"])


@router.get("/")
async def get_plants(
        current_user: CurrentUserDep,
        session: SessionDep
):
    statement = select(Plant).where(Plant.owner == current_user.id)
    results = session.exec(statement)
    return results.all()


@router.post("/")
async def register_plant(
        name: Annotated[str, Form()],
        image: UploadFile,
        current_user: CurrentUserDep,
        session: SessionDep
):
    asset = await upload_image_to_asset(
        image=image,
        current_user=current_user,
        session=session
    )

    user_plant = Plant(
        owner=current_user.id,
        name=name,
        avatar_asset_id=asset.id,
    )
    session.add(asset)
    session.add(user_plant)
    session.commit()

    return SuccessResponse()


@router.delete("/{plant_id}/updates/{update_id}")
async def delete_update(
        plant_id: uuid.UUID,
        update_id: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep
) -> SuccessResponse:
    plant = session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )

    if plant.owner != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to access this plant"
        )

    plant_update = session.get(PlantUpdate, update_id)
    if plant_update is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant Update not found"
        )

    if plant_update.plant_id != plant.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The update id does not correspond to the plant"
        )

    asset = session.get(Asset, plant_update.asset_id)

    try:
        session.delete(asset)
        session.delete(plant_update)
        session.commit()
    finally:
        try_delete_asset(minio_client, asset.asset_hash)

    return SuccessResponse()


@router.post("/{plant_id}/updates")
async def publish_update(
        plant_id: uuid.UUID,
        image: UploadFile,
        current_user: CurrentUserDep,
        session: SessionDep
):
    plant = session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )

    if plant.owner != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to access this plant"
        )

    # TODO / IDEA: only allow one update per day (offer to replace existing in frontend)

    asset = await upload_image_to_asset(
        image=image,
        current_user=current_user,
        session=session
    )

    plant_update = PlantUpdate(
        plant_id=plant_id,
        asset_id=asset.id,
    )

    session.add(asset)
    session.add(plant_update)
    session.commit()

    return SuccessResponse()


def assert_plant_read_permission(
        plant: Plant,
        current_user: CurrentUserDep,
        session: SessionDep
) -> None:
    # check plant owner
    if plant.owner == current_user.id:
        return

    # if owner != current user check follower status
    follow_request = session.get(Follower, (current_user.id, plant.owner))
    if follow_request is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to access this plant"
        )

    # if current user is not an approved follower reject access
    if follow_request.status != FollowStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to access this plant"
        )


@router.get("/{plant_id}/updates")
async def get_plant_updates(
        plant_id: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep,
        offset: int = 0,
        limit: int = Query(default=10, le=20),

) -> list[PlantUpdate]:
    # Get plant by primary key
    plant = session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )

    # ensure current user can read plant
    assert_plant_read_permission(plant, current_user, session)

    query = select(PlantUpdate).where(PlantUpdate.plant_id == plant.id).offset(offset).limit(limit)
    return session.exec(query).all()


@router.get("/{plant_id}")
async def get_plant_details(
        plant_id: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep
) -> Plant:
    # Get plant by primary key
    plant = session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )

    # ensure current user can read plant
    assert_plant_read_permission(plant, current_user, session)

    return plant
