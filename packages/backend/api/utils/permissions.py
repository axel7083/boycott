import uuid

from fastapi import HTTPException
from sqlmodel import Session
from starlette import status

from models.tables.follower import Follower, FollowStatus
from models.tables.plant import Plant
from models.tables.user import User


def assert_is_follower(
        from_user_id: uuid.UUID,
        to_user_id:  uuid.UUID,
        session: Session
) -> None:
    # if owner != current user check follower status
    follow_request = session.get(Follower, (from_user_id, to_user_id))
    if follow_request is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to access this plant"
        )

    # if the current user is not an approved follower reject access
    if follow_request.status != FollowStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to access this plant"
        )


def assert_plant_read_permission(
        plant: Plant,
        user: User,
        session: Session
) -> None:
    """
    Asserts if the user has permission to read the specified plant.
    """
    # check plant owner
    if plant.owner == user.id:
        return

    # if owner != current user check follower status
    assert_is_follower(
        from_user_id=user.id,
        to_user_id=plant.owner,
        session=session,
    )