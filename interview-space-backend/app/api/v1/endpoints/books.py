from http import HTTPStatus
import json
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException
from app.core.database import get_db
from app.models.books import Books as BooksModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


router = APIRouter()


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


@router.post("/", response_model=BooksResponse, status_code=HTTPStatus.CREATED)
async def create_books(
    request: BooksCreate, db: AsyncSession = Depends(get_db)
) -> BooksResponse:
    try:
        result = await db.execute(
            select(BooksModel).where(BooksModel.name == request.name)
        )
        books = result.scalar_one_or_none()
        if books:
            raise HTTPException(
                detail="Book already exists",
                status_code=HTTPStatus.CONFLICT,
            )

        books = BooksModel(**request.model_dump())
        db.add(books)
        await db.commit()
        await db.refresh(books)

        return BooksResponse.model_validate(books)
    except HTTPException:
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            detail="Book could not be created because it violates a database constraint",
            status_code=HTTPStatus.CONFLICT,
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            detail="Database error while creating book",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            detail="Unexpected error while creating book",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc


@router.get("/", response_model=list[BooksResponse], status_code=HTTPStatus.OK)
async def fetch_books(db: AsyncSession = Depends(get_db)) -> list[BooksResponse]:
    try:
        books = await db.execute(select(BooksModel))
        response = books.scalars().all()

        return [BooksResponse.model_validate(book) for book in response]
    except SQLAlchemyError as exc:
        raise HTTPException(
            detail="Database error while fetching books",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            detail="Unexpected error while fetching books",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc


@router.get(
    "/search", response_model=list[BooksResponse], status_code=HTTPStatus.ACCEPTED
)
async def search_results(
    query: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
) -> list[BooksResponse]:
    try:
        books_search = await db.execute(
            select(BooksModel).where(BooksModel.name.ilike(f"{query}%"))
        )
        result = books_search.scalars().all()

        return [BooksResponse.model_validate(book) for book in result]
    except SQLAlchemyError as exc:
        raise HTTPException(
            detail="Database error while searching books",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            detail="Unexpected error while searching books",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc


@router.patch(
    "/{book_id}", response_model=BooksResponse, status_code=HTTPStatus.ACCEPTED
)
async def update_book(
    book_id: int, request: UpdateBook, db: AsyncSession = Depends(get_db)
) -> BooksResponse:
    try:
        book = await db.execute(
            select(BooksModel).where(BooksModel.id == book_id).with_for_update()
        )
        result = book.scalar_one_or_none()

        if result is None:
            raise HTTPException(
                detail="Book not found",
                status_code=HTTPStatus.NOT_FOUND,
            )

        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                detail="At least one field is required to update a book",
                status_code=HTTPStatus.BAD_REQUEST,
            )

        for field, value in update_data.items():
            setattr(result, field, value)

        await db.commit()
        await db.refresh(result)

        return BooksResponse.model_validate(result)
    except HTTPException:
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            detail="Book could not be updated because it violates a database constraint",
            status_code=HTTPStatus.CONFLICT,
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            detail="Database error while updating book",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            detail="Unexpected error while updating book",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc


@router.delete("/{book_id}", response_model=MessageResponse, status_code=HTTPStatus.OK)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(BooksModel).where(BooksModel.id == book_id))
        book = result.scalar_one_or_none()
        if book is None:
            raise HTTPException(
                detail="Book not found",
                status_code=HTTPStatus.NOT_FOUND,
            )

        await db.delete(book)
        await db.commit()

        return {"message": "Book deleted successfully"}
    except HTTPException:
        raise
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            detail="Book could not be deleted because it violates a database constraint",
            status_code=HTTPStatus.CONFLICT,
        ) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(
            detail="Database error while deleting book",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            detail="Unexpected error while deleting book",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        ) from exc


def read_books_file():
    with open("app/assets/books.json", "r") as file:
        books = json.load(file)
        return books


@router.get("/book_search", response_model=list[BooksResponse])
def get_books_from_file(
    q: str = Query(default=""),
    skip: int = Query(),
    limit: int = Query(),
    db: AsyncSession = Depends(get_db),
):
    books = read_books_file()
    print(books)

    books = books[skip : skip + limit]

    return [BooksResponse.model_validate(book) for book in books]
