from typing import Protocol
from uuid import UUID
import uuid
import aioboto3
from fastapi import Request
from app.core.config import settings

class ObjectStoreProtocol(Protocol):
    async def upload_file(self, workspace_id: UUID, file_bytes: bytes, filename: str) -> str:
        ...
        
    async def download_file(self, file_uri: str) -> bytes:
        ...

class S3ObjectStore:
    def __init__(self, s3_client):
        self.s3_client = s3_client
        self.bucket = settings.S3_BUCKET

    async def upload_file(self, workspace_id: UUID, file_bytes: bytes, filename: str) -> str:
        file_uuid = uuid.uuid4()
        object_key = f"{workspace_id}/{file_uuid}-{filename}"
        
        await self.s3_client.put_object(
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
            
        response = await self.s3_client.get_object(Bucket=self.bucket, Key=object_key)
        return await response["Body"].read()

def get_object_store(request: Request) -> ObjectStoreProtocol:
    """Dependency to provide shared S3ObjectStore from app state."""
    return S3ObjectStore(request.app.state.s3_client)
