from fastapi import APIRouter, UploadFile
from pydantic import BaseModel
from sqlmodel import select
from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from api.utils.image import upload_image_to_asset
from models.sucess_response import SuccessResponse
from models.tables.plant import Plant

router = APIRouter(prefix="/plants", tags=["plants"])

@router.get("/")
async def get_plants(
        current_user: CurrentUserDep,
        session: SessionDep
):
    statement = select(Plant).where(Plant.owner == current_user.id)
    results = session.exec(statement)
    return results.all()

class RegisterPlant(BaseModel):
    name: str

@router.post("/")
async def register_plant(
        body: RegisterPlant,
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
        name=body.name,
        avatar_asset_id=asset.id,
    )
    session.add(asset)
    session.add(user_plant)
    session.commit()

    return SuccessResponse()
