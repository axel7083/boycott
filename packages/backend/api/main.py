from fastapi import APIRouter

from api.routes import users, assets, stories

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(assets.router)
api_router.include_router(stories.router)
