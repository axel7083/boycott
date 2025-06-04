from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from api.main import api_router
from core.minio import init_buckets
from core.settings import settings
from core.db import init_db

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()
    init_buckets()

if settings.RESTRICT_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS,
    )

app.include_router(api_router, prefix=settings.API_V1_STR)