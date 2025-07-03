import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column
from sqlmodel import SQLModel, Field, Enum as DBEnum

class FollowStatus(str, Enum):
    PENDING = "pending"
    REJECTED = "rejected"
    APPROVED = "approved"


class Follower(SQLModel, table=True):
    from_user: uuid.UUID = Field(foreign_key="user.id", primary_key=True, index=True)
    to_user: uuid.UUID = Field(foreign_key="user.id", primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    status: FollowStatus = Field(default=FollowStatus.PENDING, sa_column=Column(DBEnum(FollowStatus)))