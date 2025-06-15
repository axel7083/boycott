from pydantic import BaseModel

class Usage(BaseModel):
    asset_size_sum: int
    asset_size_limit: int