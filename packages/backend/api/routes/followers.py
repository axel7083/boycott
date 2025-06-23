import uuid

from fastapi import APIRouter, HTTPException

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from models.follow_request import FollowRequest, FollowRequestStatus
from models.follower import Follower
from sqlmodel import select
from starlette import status

router = APIRouter(prefix="/followers", tags=["followers"])

@router.post("/accept/{user_id}")
async def accept_follower(
        user_id: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep
):
    # Get follow request from user_id to current
    follow_request = session.get(FollowRequest, (user_id, current_user.id))
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

    return {"success": True}

@router.get("/pending")
async def get_pending_followers(
        current_user: CurrentUserDep,
        session: SessionDep
):
    statement = (select(FollowRequest)
                 .where(FollowRequest.to_user == current_user.id)
                 .where(FollowRequest.status == FollowRequestStatus.PENDING)
                 )
    return session.exec(statement).all()
