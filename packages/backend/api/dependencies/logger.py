import logging
from typing import Annotated

from fastapi import Depends

logger = logging.getLogger('uvicorn.error')

def get_logger() -> logging.Logger:
    return logger

LoggerDep = Annotated[logging.Logger, Depends(get_logger)]