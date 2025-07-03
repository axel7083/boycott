from fastapi import APIRouter

from api.routes import users, assets, stories, followers, followings, avatars

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(assets.router)
api_router.include_router(stories.router)
api_router.include_router(followers.router)
api_router.include_router(followings.router)
api_router.include_router(avatars.router)
