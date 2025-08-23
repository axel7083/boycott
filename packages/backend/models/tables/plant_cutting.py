import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class PlantCutting(SQLModel, table=True):
    parent_id: uuid.UUID = Field(foreign_key="plant.id", primary_key=True)
    cutting_id: uuid.UUID = Field(foreign_key="plant.id", primary_key=True)

    created_at: datetime = Field(default_factory=datetime.now)

