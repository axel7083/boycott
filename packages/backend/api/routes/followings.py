import uuid
from fastapi import APIRouter, HTTPException

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from models.sucess_response import SuccessResponse
from models.tables.follower import Follower, FollowStatus
from models.tables.user import User
from starlette import status

router = APIRouter(prefix="/followings", tags=["followings"])

@router.post("/request/{to_user}")
async def follow(
        to_user: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep
) -> SuccessResponse:
    if to_user == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )

    user = session.get(User, to_user)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    follower = session.get(Follower, (current_user.id, to_user))
    if follower is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )

    follow_request = session.get(Follower, (current_user.id, to_user))
    if follow_request is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already have pending request"
        )

    # TODO: handle public account

    follow_request = Follower(
        from_user=current_user.id,
        to_user=to_user
    )
    session.add(follow_request)
    session.commit()

    return SuccessResponse()

@router.get("/request/{to_user}/status")
async def get_follow_status(
        to_user: uuid.UUID,
        current_user: CurrentUserDep,
        session: SessionDep
) -> FollowStatus:
    follow_request = session.get(Follower, (current_user.id, to_user))
    if follow_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such follow request"
        )

    return follow_request

