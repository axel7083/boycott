import uuid
from typing import Annotated

from fastapi import APIRouter, UploadFile, Form, HTTPException, Query
from sqlmodel import select, delete, update
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

    statement = (select(Plant)
                 .where(Plant.owner == target_user)
                 .order_by(Plant.updated_at.desc())
                 )

    return session.exec(statement).all()


@router.post("/")
async def register_plant(
        current_user: CurrentUserDep,
        session: SessionDep,
        name: Annotated[str, Form()],
        image: UploadFile,
        parent_id: Annotated[uuid.UUID | None, Form(
            title="Parent Plant ID",
        )] = None,
) -> Plant:
    # if the user provided parent_id, get the corresponding plant
    parent: Plant | None = session.get(Plant, parent_id) if parent_id is not None else None

    # ensure the current is the parent plant owner
    if parent is not None and parent.owner != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to access parent plant"
        )

    # upload asset to minio
    asset = await upload_image_to_asset(
        image=image,
        current_user=current_user,
        session=session
    )

    # create
    user_plant = Plant(
        owner=current_user.id,
        name=name,
        asset_id=asset.id,
        parent_id=parent.id if parent is not None else None,
    )

    plant_update = PlantUpdate(
        plant_id=user_plant.id,
        asset_id=asset.id,
    )

    session.add(asset)
    session.add(user_plant)
    session.add(plant_update)

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

    # Remove all reference to this plant from other Plant objects
    update_statement = update(Plant).where(Plant.parent_id == plant.id).values(parent_id=None)
    session.exec(update_statement)
    session.commit()

    # Get all PlantUpdate objects associated with this plant & corresponding assets
    statement = select(PlantUpdate, Asset).join(Asset, onclause=(PlantUpdate.asset_id == Asset.id)).where(PlantUpdate.plant_id == plant.id)
    items: list[tuple[PlantUpdate, Asset]] = session.exec(statement).all()

    # Delete PlantUpdate Objects (to free PlantUpdate#asset_id foreign key contraint)
    for plant_update, _ in items:
        session.delete(plant_update)
    session.commit()

    # Delete Plant Object to free Plant#asset_id foreign key contraint
    session.delete(plant)
    session.commit()

    # Delete dangling assets
    for _, asset in items:
        # Delete corresponding object in storage
        try_delete_asset(minio_client, asset)

        session.delete(asset)
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
