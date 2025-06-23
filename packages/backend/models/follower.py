import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field

class Follower(SQLModel, table=True):
    from_user: uuid.UUID = Field(foreign_key="user.id", primary_key=True, index=True)
    to_user: uuid.UUID = Field(foreign_key="user.id", primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)