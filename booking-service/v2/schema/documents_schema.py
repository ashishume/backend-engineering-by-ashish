from pydantic import BaseModel


class DocumentsCreate(BaseModel):
    file_name: str
    file_type: str
    file: bytes
