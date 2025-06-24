import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column
from sqlmodel import SQLModel, Field, Enum as DBEnum

class FollowRequestStatus(str, Enum):
    PENDING = "pending"
    REJECTED = "rejected"

class FollowRequest(SQLModel, table=True):
    from_user: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    to_user: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    status: FollowRequestStatus = Field(default=FollowRequestStatus.PENDING, sa_column=Column(DBEnum(FollowRequestStatus)))
    created_at: datetime = Field(default_factory=datetime.now)