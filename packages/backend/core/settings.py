import secrets
from typing import Annotated, List

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "TWFzSQHLdI_NGJT2sWMC_iKswcu9TfTWWw8hW4_Iwwc"
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
    RESTRICT_HOSTS: bool = False
    TRUSTED_HOSTS: Annotated[List[str], NoDecode] = []

    # asset configuration
    MAX_IMAGE_SIZE: int = 5 * 1024 * 1024  # 5MB
    MAX_SUM_STORAGE: int = MAX_IMAGE_SIZE * 20 # 100MB

    @field_validator('TRUSTED_HOSTS', mode='before')
    @classmethod
    def decode_trusted_hosts(cls, raw: str | list[str]) -> list[str]:
        if type(raw) is str:
            return [host for host in raw.split(',')]
        else:
            return raw

settings = Settings()  # type: ignore