from sqlmodel import create_engine, SQLModel
import packages.backend.models # required

engine = create_engine("postgresql+psycopg://testUser:testPassword@localhost:5432/testDB")

def init_db() -> None:
    SQLModel.metadata.create_all(engine)