import uuid

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, max_length=64)
    password_hash: str = Field(max_length=255)