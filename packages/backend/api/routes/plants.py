import uuid
from typing import Annotated

from fastapi import APIRouter, UploadFile, Form, HTTPException, Query
from sqlmodel import select
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.image import upload_image_to_asset
from api.utils.minio import try_delete_asset
from api.utils.permissions import assert_plant_read_permission, assert_is_follower
from core.minio import minio_client
from models.sucess_response import SuccessResponse
from models.tables.asset import Asset
from models.tables.plant import Plant
from models.tables.plant_cutting import PlantCutting
from models.tables.plant_update import PlantUpdate

router = APIRouter(prefix="/plants", tags=["plants"])

@router.get("/")
async def get_plants(
        current_user: CurrentUserDep,
        session: SessionDep,
        user_id: uuid.UUID | None = Query(default=None),
) -> list[Plant]:
    target_user: uuid.UUID = user_id if user_id is not None else current_user.id
    if target_user != current_user.id:
        assert_is_follower(
            from_user_id=current_user.id,
            to_user_id=user_id,
            session=session,
        )

    statement = select(Plant).where(Plant.owner == target_user)

    return session.exec(statement).all()


@router.post("/")
async def register_plant(
        current_user: CurrentUserDep,
        session: SessionDep,
        name: Annotated[str, Form()],
        image: UploadFile,
        parent: Annotated[uuid.UUID | None, Form(
            title="Parent Plant ID",
        )] = None,
) -> Plant:
    asset = await upload_image_to_asset(
        image=image,
        current_user=current_user,
        session=session
    )

    user_plant = Plant(
        owner=current_user.id,
        name=name,
        asset_id=asset.id,
    )

    plant_update = PlantUpdate(
        plant_id=user_plant.id,
        asset_id=asset.id,
    )

    cutting = None
    if parent is not None:
        assert_plant_read_permission(
            plant=session.get(Plant, parent),
            user=current_user,
            session=session,
        )
        cutting = PlantCutting(
            parent_id=parent,
            cutting_id=user_plant.id,
        )

    session.add(asset)
    session.add(user_plant)
    session.add(plant_update)

    if cutting is not None:
        session.add(cutting)

    session.commit()
    session.refresh(user_plant)

    return user_plant


@router.delete("/{plant_id}")
async def delete_plant(
        plant_id: uuid.UUID,
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

    statement = select(PlantUpdate, Asset).join(Asset, onclause=(PlantUpdate.asset_id == Asset.id)).where(PlantUpdate.plant_id == plant.id)
    items: list[tuple[PlantUpdate, Asset]] = session.exec(statement).all()

    for update, asset in items:
        try:
            session.delete(update)
            session.commit()

            session.delete(asset)
            session.commit()
        finally:
            try_delete_asset(minio_client, asset.asset_hash)

    # Delete all plant updates
    session.delete(plant)
    session.commit()

    return SuccessResponse()


@router.get("/{plant_id}")
async def get_plant(
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

    # ensure the current user can read plant
    assert_plant_read_permission(plant, current_user, session)

    return plant
