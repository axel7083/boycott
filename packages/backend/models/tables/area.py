import uuid
from datetime import datetime

from sqlalchemy import DateTime, Column
from sqlmodel import Field, SQLModel


class Area(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    owner: uuid.UUID = Field(foreign_key="user.id")
    name: str = Field(max_length=64)

    outdoor: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(), onupdate=datetime.now)
    )

