import uuid

from sqlmodel import Field, SQLModel

class Images(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    user_id: uuid.UUID = Field(default=None, foreign_key="user.id")
    size: int = Field(description="Size in bytes of the image")