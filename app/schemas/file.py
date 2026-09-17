from pydantic import BaseModel

class FileUploadResponse(BaseModel):
    file_uri: str
    filename: str
    size: int
