from typing import Annotated

from fastapi import Header, HTTPException, Depends, Response
from starlette import status


class ETagCache:
    def __init__(
            self,
            if_none_match: str | None,
            response: Response
    ):
        self.if_none_match = if_none_match
        self.response = response

    def verify(self, etag: str):
        # Check if the client has the same ETag (If-None-Match header)
        if self.if_none_match == etag:
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, headers={
                "Cache-Control": "private",
            })  # Not Modified

        # append the ETag to the response headers
        self.response.headers["ETag"] = etag
        self.response.headers["Cache-Control"] = "private, must-revalidate"


async def get_etag_cache(
        response: Response,
        if_none_match: Annotated[str | None, Header()] = None,
) -> ETagCache:
    return ETagCache(if_none_match, response)

ETagCacheDep = Annotated[ETagCache, Depends(get_etag_cache)]