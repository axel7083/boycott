from fastapi import FastAPI, Request, HTTPException
from starlette import status

from api.main import api_router
from core.minio import init_buckets
from core.settings import settings
from core.db import init_db
import ipaddress

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()
    init_buckets()


@app.middleware("http")
async def validate_ip(request: Request, call_next):
    if not settings.RESTRICT_IPS:
        return await call_next(request)

    # Get client IP
    client_ip = str(request.client.host)

    try:
        # Convert client IP to IP address object
        ip_addr = ipaddress.ip_address(client_ip)

        # Check if IP is in any of the allowed networks
        is_allowed = any(
            ip_addr in ipaddress.ip_network(allowed_range)
            for allowed_range in settings.WHITELISTED_IPS
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"IP {client_ip} is not allowed to access this resource."
            )

        return await call_next(request)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid IP address format"
        )


app.include_router(api_router, prefix=settings.API_V1_STR)