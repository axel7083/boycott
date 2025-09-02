import uuid
from datetime import datetime

from pydantic import field_validator
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel
from cron_converter import Cron

class Plant(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    owner: uuid.UUID = Field(foreign_key="user.id")
    name: str = Field(max_length=64)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(), onupdate=datetime.now)
    )

    dead: bool = Field(default=False)

    # latest asset id
    asset_id: uuid.UUID | None = Field(default=None, foreign_key="asset.id")
    # parent plant id
    parent_id: uuid.UUID | None = Field(default=None, foreign_key="plant.id")

    # cron format
    water_schedule: str | None = Field(default=None, max_length=64)

    @field_validator('water_schedule')
    @classmethod
    def validate_cron_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            Cron(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid cron format: {e}")
