from sqlmodel import Session, select

from core.settings import settings
from models.usage import Usage
from models.tables.story import Story
from models.tables.user import User


def get_user_usage(user: User, session: Session) -> Usage:
    statement = select(Story).where(Story.author == user.id)

    results = session.exec(statement)

    asset_size_sum = 0
    for story in results:
        asset_size_sum = asset_size_sum + story.asset_size

    return Usage(asset_size_sum=asset_size_sum, asset_size_limit=settings.MAX_SUM_STORAGE)