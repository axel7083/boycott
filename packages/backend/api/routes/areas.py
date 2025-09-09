import uuid
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Header, Response
from starlette import status

from api.dependencies.current_user import CurrentUserDep
from api.dependencies.session import SessionDep
from models.tables.area import Area
from sqlmodel import select, Session, func

from models.tables.user import User

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
        response: Response,
        # etag
        if_none_match: Annotated[str | None, Header()] = None,
) -> list[Area]:
    # Get the ETAG for the request
    etag = list_area_etag(current_user.id, session)

    # Check if the client has the same ETag (If-None-Match header)
    if if_none_match == etag:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, headers={
            "Cache-Control": "private",
        })  # Not Modified

    # append the ETag to the response headers
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, must-revalidate"

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