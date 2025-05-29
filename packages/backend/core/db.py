from sqlmodel import create_engine, SQLModel
from models.user import User # required
from models.images import Images # required

engine = create_engine("postgresql+psycopg://testUser:testPassword@localhost:5432/testDB")

def init_db() -> None:
    SQLModel.metadata.create_all(engine)