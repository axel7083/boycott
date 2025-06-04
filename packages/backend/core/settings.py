import secrets
from typing import Annotated, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    # bucket to store the images
    IMAGES_BUCKET: str = "images"

    # postgres credentials
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "testDB"
    POSTGRES_USER: str = "testUser"
    POSTGRES_PASSWORD: str = "testPassword"

    # minio credentials
    MINIO_HOST: str = "localhost"
    MINIO_PORT: int = 9000
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = "Password1234"
    MINIO_SECURE: bool = False

    # prevent unauthorized access
    RESTRICT_IPS: bool = False
    WHITELISTED_IPS: Annotated[List[str], NoDecode] = []

    @field_validator('WHITELISTED_IPS', mode='before')
    @classmethod
    def decode_white_listed_ips(cls, raw: str) -> list[str]:
        return [ip for ip in raw.split(',')]

settings = Settings()  # type: ignore