import uuid
from enum import Enum

from sqlalchemy import Column

from sqlmodel import Field, SQLModel, Enum as DBEnum

class AssetType(str, Enum):
    IMAGE_JPEG = "image/jpeg"

class AssetVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class Asset(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    author: uuid.UUID = Field(foreign_key="user.id")

    # etag is computed by Minio
    asset_etag: str = Field(max_length=64, min_length=64)
    asset_size: int = Field()
    asset_type: AssetType = Field(sa_column=Column(DBEnum(AssetType)))
    asset_visibility: AssetVisibility = Field(default=AssetVisibility.PRIVATE, sa_column=Column(DBEnum(AssetVisibility)))