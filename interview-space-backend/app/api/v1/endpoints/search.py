from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr
from typing import List
from datetime import datetime
import json

router = APIRouter()


class UserModel(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    city: str
    country: str
    company: str
    job_title: str
    created_at: datetime
    is_active: bool
    tags: List[str]
    score: float


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    email: str
    phone: str

class ResponseModel(BaseModel):
    message: str
    data: List[UserResponse]


def load_data():
    with open("sample_data.json", "r") as file:
        data = json.load(file)
        return data


@router.get("/", response_model=ResponseModel)
def search_users(name: str = Query(default="")):
    data = load_data()

    filtered_data = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "email": item.get("email"),
            "phone": item.get("phone"),
        }
        for item in data
        if item.get("name", "").startswith(name)
    ]

    return ResponseModel(message="Users searched successfully", data=filtered_data)