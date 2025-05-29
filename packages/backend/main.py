from fastapi import FastAPI

from api.main import api_router
from core.minio import init_buckets
from core.settings import settings
from core.db import init_db

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()
    init_buckets()

app.include_router(api_router, prefix=settings.API_V1_STR)