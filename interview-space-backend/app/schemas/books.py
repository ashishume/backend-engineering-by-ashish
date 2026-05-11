from typing import Optional
from pydantic import BaseModel


class BooksCreate(BaseModel):
    name: str
    author: str
    description: str


class BooksResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    author: str
    description: str


class UpdateBook(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


class PasswordChecker(BaseModel):
    password: str
