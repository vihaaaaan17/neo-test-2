from typing import Protocol
from uuid import UUID
import uuid
import aioboto3
from app.core.config import settings

class ObjectStoreProtocol(Protocol):
    async def upload_file(self, workspace_id: UUID, file_bytes: bytes, filename: str) -> str:
        ...
        
    async def download_file(self, file_uri: str) -> bytes:
        ...

class S3ObjectStore:
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET
        self.endpoint_url = settings.S3_ENDPOINT_URL

    async def upload_file(self, workspace_id: UUID, file_bytes: bytes, filename: str) -> str:
        file_uuid = uuid.uuid4()
        object_key = f"{workspace_id}/{file_uuid}-{filename}"
        
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3_client:
            await s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=file_bytes
            )
        
        return f"s3://{self.bucket}/{object_key}"

    async def download_file(self, file_uri: str) -> bytes:
        if not file_uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI")
        
        path = file_uri[5:]
        bucket_name, object_key = path.split("/", 1)
        
        if bucket_name != self.bucket:
            raise ValueError(f"Expected bucket {self.bucket}, got {bucket_name}")
            
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3_client:
            response = await s3_client.get_object(Bucket=self.bucket, Key=object_key)
            return await response["Body"].read()

def get_object_store() -> ObjectStoreProtocol:
    return S3ObjectStore()
