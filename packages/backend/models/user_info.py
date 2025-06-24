import uuid

from pydantic import BaseModel

class UserInfo(BaseModel):
    id: uuid.UUID
    username: str
    avatar_asset_id: uuid.UUID | None