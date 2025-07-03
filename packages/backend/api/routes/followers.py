import uuid

from fastapi import APIRouter, HTTPException

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from models.sucess_response import SuccessResponse
from models.tables.follower import Follower, FollowStatus
from sqlmodel import select
from starlette import status

from models.tables.user import User
from models.user_info import UserInfo

router = APIRouter(prefix="/followers", tags=["followers"])

@router.post("/accept/{user_id}")
async def accept_follower(
        user_id: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep
):
    # Get follow request from user_id to current
    follow_request = session.get(Follower, (user_id, current_user.id))
    if follow_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such follow request"
        )

    # delete follow request
    session.delete(follow_request)

    # create follower relation
    follower = Follower(
        from_user=user_id,
        to_user=current_user.id
    )
    session.add(follower)
    session.commit()

    return SuccessResponse()

@router.get("/pending")
async def get_pending_followers(
        current_user: CurrentUserDep,
        session: SessionDep
) -> list[UserInfo]:
    statement = (select(Follower, User)
                 .where(Follower.to_user == current_user.id)
                 .where(Follower.status == FollowStatus.PENDING)
                 .where(Follower.from_user == User.id) # joining tables
                 )

    return [
        UserInfo(
            id=user.id,
            avatar_id=user.avatar_asset_id,
            username=user.username,
        ) for request, user in session.exec(statement)
    ]
