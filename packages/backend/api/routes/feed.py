import datetime
import uuid

from fastapi import APIRouter, UploadFile, Form, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from sqlmodel import select

from models.tables.follower import Follower, FollowStatus
from models.tables.plant import Plant
from models.tables.plant_update import PlantUpdate
from models.tables.user import User

router = APIRouter(prefix="/feed", tags=["feed"])

class FeedItemAuthor(BaseModel):
    id: uuid.UUID
    username: str

class FeedItem(BaseModel):
    id: uuid.UUID
    created_at: datetime.datetime
    asset_id: uuid.UUID
    author: FeedItemAuthor

@router.get("/")
async def get_feed(
        current_user: CurrentUserDep,
        session: SessionDep
):
    # Step 1: Subquery for followers
    follower_subq = (select(Follower.to_user)
                     .where(Follower.from_user == current_user.id)
                     .where(Follower.status == FollowStatus.APPROVED)
                     )

    # Step 2: Final query for plant updates
    statement = (
        select(
            PlantUpdate,
            Plant,
            User,
        )
        .join(Plant, onclause=(Plant.id == PlantUpdate.plant_id))
        .join(User, onclause=(User.id == Plant.owner))
        .where(Plant.owner.in_(follower_subq))
        .where(PlantUpdate.created_at > func.now() - datetime.timedelta(hours=24))  # ⬅️ NEW CONDITION
    )

    results: list[tuple[PlantUpdate,Plant,User]] = session.exec(statement).all()
    return [FeedItem(
        id=plantUpdate.id,
        created_at=plantUpdate.created_at,
        asset_id=plantUpdate.asset_id,
        author=FeedItemAuthor(id=user.id, username=user.username),
    ) for (plantUpdate, plant, user) in results]