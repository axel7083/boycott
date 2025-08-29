import uuid

from fastapi import APIRouter, HTTPException
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.permissions import assert_plant_read_permission
from models.tables.plant import Plant

from sqlmodel import select
router = APIRouter(prefix="/cuttings", tags=["cuttings"])

@router.get("/{plant_id}")
async def get_plant_cuttings(
        plant_id: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep,
) -> list[Plant]:
    # Get plant by id
    plant = session.get(Plant, plant_id)
    if plant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plant not found"
        )

    assert_plant_read_permission(
        plant=plant,
        user=current_user,
        session=session,
    )

    statement = (select(Plant)
                 .where(Plant.parent_id == plant.id))
    return session.exec(statement).all()