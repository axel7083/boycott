from minio import Minio

from core.settings import settings

minio_client = Minio(
    "{host}:{port}".format(host=settings.MINIO_HOST, port=settings.MINIO_PORT),
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=settings.MINIO_SECURE,
)

def init_buckets() -> None:
    if not minio_client.bucket_exists(settings.IMAGES_BUCKET):
        minio_client.make_bucket(settings.IMAGES_BUCKET)
