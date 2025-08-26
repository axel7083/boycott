import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

class Plant(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    owner: uuid.UUID = Field(foreign_key="user.id")
    name: str = Field(unique=True, max_length=64)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(), onupdate=datetime.now)
    )

    dead: bool = Field(default=False)

    # latest asset id
    asset_id: uuid.UUID | None = Field(default=None, foreign_key="asset.id")