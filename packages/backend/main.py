from fastapi import FastAPI

from packages.backend.api.main import api_router
from packages.backend.core.settings import settings
from packages.backend.core.db import init_db

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(api_router, prefix=settings.API_V1_STR)