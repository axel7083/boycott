from sqlmodel import Session, select

from core.settings import settings
from models.tables.asset import Asset
from models.usage import Usage
from models.tables.story import Story
from models.tables.user import User

def get_user_usage(user: User, session: Session) -> Usage:
    statement = (select(Story, Asset)
                 .where(Story.author == user.id)
                 .where(Story.asset_id == Asset.id)
                 )

    results = session.exec(statement)

    asset_size_sum = 0
    for story, asset in results:
        asset_size_sum = asset_size_sum + asset.asset_size

    return Usage(asset_size_sum=asset_size_sum, asset_size_limit=settings.MAX_SUM_STORAGE)