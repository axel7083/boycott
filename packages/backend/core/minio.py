from minio import Minio

from core.settings import settings

client = Minio("localhost:9000", access_key="admin", secret_key="Password1234", secure=False)

def init_buckets() -> None:
    if not client.bucket_exists(settings.IMAGES_BUCKET):
        client.make_bucket(settings.IMAGES_BUCKET)