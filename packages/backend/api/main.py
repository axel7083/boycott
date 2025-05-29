from fastapi import APIRouter

from packages.backend.api.routes import users

api_router = APIRouter()
api_router.include_router(users.router)
