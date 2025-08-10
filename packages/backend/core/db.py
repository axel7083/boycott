from sqlmodel import create_engine, SQLModel

from core.settings import settings
from models import * # type: ignore

def get_engine_url() -> str:
    return "postgresql+psycopg://{username}:{password}@{host}:{port}/{db_name}".format(
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        db_name=settings.POSTGRES_DB,
    )

engine = create_engine(
    get_engine_url(),
    echo=False,  # Enable SQL query logging
    pool_pre_ping=True,  # Enable connection health checks
    connect_args={"connect_timeout": 5}  # Add connection timeout
)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)