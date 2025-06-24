import uuid

from pydantic import BaseModel

class UserInfo(BaseModel):
    id: uuid.UUID
    username: str
    avatar_id: uuid.UUID