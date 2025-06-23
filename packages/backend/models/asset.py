import uuid
from enum import Enum

from sqlalchemy import Column

from sqlmodel import Field, SQLModel, Enum as DBEnum

class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"

class Asset(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    asset_hash: str = Field(max_length=64, min_length=64)
    asset_size: int = Field()
    asset_type: AssetType = Field(sa_column=Column(DBEnum(AssetType)))