from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Header
from jwt import InvalidTokenError
from pydantic import ValidationError
from starlette import status

from packages.backend.api.dependencies.session import SessionDep
from packages.backend.core import security
from packages.backend.core.settings import settings
from packages.backend.models import User, TokenPayload

async def get_current_user(session: SessionDep, authorization: Annotated[str | None, Header()] = None) -> User:
    # Extract Bearer token
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.split(" ")[1]  # Extract the token after 'Bearer'

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    except:
        raise HTTPException(
            status_code=status.WS_1011_INTERNAL_ERROR,
            detail="Something went wrong while trying to validate the token"
        )

    user: User | None = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]