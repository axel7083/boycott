import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

class Story(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    author: uuid.UUID = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)
    # might be nice in the future to have a dedicated asset table
    asset_hash: str = Field(max_length=64, min_length=64)