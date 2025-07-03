from models.tables.follower import FollowStatus
from models.user_info import UserInfo

class UserInfoSearch(UserInfo):
    follow_status: FollowStatus | None
