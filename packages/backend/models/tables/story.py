import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

class Story(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    author: uuid.UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)

    asset_id: uuid.UUID = Field(foreign_key="asset.id")