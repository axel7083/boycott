import uuid
from typing import Annotated

from fastapi import APIRouter, UploadFile, Form, HTTPException, Query
from sqlmodel import select
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.image import upload_image_to_asset
from api.utils.minio import try_delete_asset
from core.minio import minio_client
from models.sucess_response import SuccessResponse
from models.tables.asset import Asset
from models.tables.follower import Follower, FollowStatus
from models.tables.plant import Plant
from models.tables.plant_update import PlantUpdate

router = APIRouter(prefix="/plants", tags=["plants"])

class PlantDetail(Plant):
    asset_id: uuid.UUID | None


@router.get("/")
async def get_plants(
        current_user: CurrentUserDep,
        session: SessionDep
) -> list[PlantDetail]:
    # Subquery to get the latest plant update for each plant
    latest_update_subquery = (
        select(
            PlantUpdate.plant_id,
            PlantUpdate.asset_id,
            PlantUpdate.created_at
        )
        .order_by(PlantUpdate.plant_id, PlantUpdate.created_at.desc())
        .distinct(PlantUpdate.plant_id)
        .subquery()
    )

    # Main query to join plants with their latest updates
    statement = (
        select(Plant, latest_update_subquery.c.asset_id)
        .outerjoin(
            latest_update_subquery,
            Plant.id == latest_update_subquery.c.plant_id
        )
        .where(Plant.owner == current_user.id)
    )

    results = session.exec(statement).all()

    # Convert results to PlantDetail objects
    plant_details = []
    for plant, asset_id in results:
        plant_detail = PlantDetail(
            id=plant.id,
            owner=plant.owner,
            name=plant.name,
            created_at=plant.created_at,
            dead=plant.dead,
            asset_id=asset_id
        )
        plant_details.append(plant_detail)

    return plant_details


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
    )

    plant_update = PlantUpdate(
        plant_id=user_plant.id,
        asset_id=asset.id,
    )

    session.add(asset)
    session.add(user_plant)
    session.add(plant_update)
    session.commit()

    return SuccessResponse()


@router.delete("/{plant_id}")
async def delete_plant(
        plant_id: uuid.UUID,
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
        # Delete plant
        session.delete(plant_update)
        session.commit()

        # Delete corresponding asset
        session.delete(asset)
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
) -> PlantDetail:
    # Get plant by primary key
    plant = session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )

    # ensure current user can read plant
    assert_plant_read_permission(plant, current_user, session)

    statement = select(PlantUpdate).where(PlantUpdate.plant_id == plant_id).order_by(PlantUpdate.created_at.desc()).limit(1)
    plant_update: PlantUpdate = session.exec(statement).first()

    return PlantDetail(
        id=plant.id,
        owner=plant.owner,
        name=plant.name,
        created_at=plant.created_at,
        dead=plant.dead,
        asset_id=plant_update.asset_id,
    )
