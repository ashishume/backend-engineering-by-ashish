from http import HTTPStatus
import json
from typing import Optional
from app.core.redis import get_redis
from redis.asyncio import Redis

from fastapi import APIRouter, Depends, Query, HTTPException, Header
from app.core.database import get_db
from app.models.books import (
    Books as BooksModel,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.schemas.books import (
    BooksCreate,
    BooksResponse,
    PasswordChecker,
    UpdateBook,
    MessageResponse,
)


router = APIRouter()

idempotency_store = {}


@router.post("/", response_model=BooksResponse, status_code=HTTPStatus.CREATED)
async def create_books(
    request: BooksCreate,
    idempotency_key: Optional[str] = Header(None, alias="idempotency-key"),
    db: AsyncSession = Depends(get_db),
) -> BooksResponse:
    try:
        if idempotency_key:
            if idempotency_key in idempotency_store:
                raise HTTPException(
                    detail="Same book already added", status_code=HTTPStatus.CONFLICT
                )

            idempotency_store[idempotency_key] = True
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


@router.get("/{book_id:int}", response_model=BooksResponse)
async def find_books(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> BooksResponse:
    key = f"book_{book_id}"
    value = await redis_client.get(key)

    if value:
        return BooksResponse.model_validate(json.loads(value))

    res = await db.execute(select(BooksModel).where(BooksModel.id == book_id))
    book = res.scalar_one_or_none()
    if book is None:
        raise HTTPException(
            detail="Book not found",
            status_code=HTTPStatus.NOT_FOUND,
        )

    response = BooksResponse.model_validate(book)
    await redis_client.set(key, response.model_dump_json(), ex=3600)
    return response


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
