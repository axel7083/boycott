import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Query

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.etag_cache import ETagCacheDep
from api.dependencies.session import SessionDep
from api.utils.permissions import assert_is_follower
from models.tables.area import Area
from sqlmodel import select, Session, func

router = APIRouter(prefix="/areas", tags=["areas"])

def list_area_etag(
        user_id: uuid.UUID,
        session: Session,
) -> str:
    """Get the latest updated_at timestamp for user's areas."""
    statement = select(func.max(Area.updated_at)).where(Area.owner == user_id)
    result = session.exec(statement).one()

    if result is None:
        return '"0"'
    return f'"{int(result.timestamp())}"'


@router.get("/")
async def list_areas(
        current_user: CurrentUserDep,
        session: SessionDep,
        etag_cache: ETagCacheDep,
        user_id: uuid.UUID | None = Query(default=None),
) -> list[Area]:
    target_user: uuid.UUID = user_id if user_id is not None else current_user.id

    # assert permissions
    if target_user != current_user.id:
        assert_is_follower(
            from_user_id=current_user.id,
            to_user_id=user_id,
            session=session,
        )

    # Get the ETAG for the request
    etag = list_area_etag(target_user, session)
    etag_cache.verify(etag=etag)

    statement = select(Area).where(Area.owner == current_user.id)
    results = session.exec(statement)
    return results.all()


@router.post("/")
async def register_area(
        current_user: CurrentUserDep,
        session: SessionDep,
        name: Annotated[str, Form()],
        outdoor: Annotated[bool, Form()],
) -> Area:
    area = Area(
        owner=current_user.id,
        name=name,
        outdoor=outdoor,
    )
    session.add(area)
    session.commit()

    session.refresh(area)

    return area