from typing import Any, List
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session
from schemas.Movie import MovieCreate, MovieResponse
from models.movies import Movie
from database import get_db
from fastapi import Depends, HTTPException, status
from services.search_service import SearchService
import datetime

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new movie",
    response_model=MovieResponse,
)
def create_movie(movie: MovieCreate, db: Session = Depends(get_db)) -> MovieResponse:
    try:
        new_movie = Movie(**movie.model_dump())
        db.add(new_movie)
        db.commit()
        db.refresh(new_movie)

        # Sync to Elasticsearch
        # search_service = SearchService(db)
        # search_service.sync_movie_to_elasticsearch(new_movie)

        return MovieResponse.model_validate(new_movie)
    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating movie: {e}",
        )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Get all movies",
    response_model=List[MovieResponse],
)
def get_all_movies(db: Session = Depends(get_db)) -> List[MovieResponse]:
    try:
        movies = db.execute(select(Movie)).scalars().all()
        return [MovieResponse.model_validate(movie) for movie in movies]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting movies: {e}",
        )


@router.get(
    "/{movie_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a movie by id",
    response_model=MovieResponse,
)
def get_movie_by_id(movie_id: str, db: Session = Depends(get_db)) -> MovieResponse:
    try:
        movie = db.execute(
            select(Movie).where(Movie.id == movie_id)
        ).scalar_one_or_none()
        if movie is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
            )
        return MovieResponse.model_validate(movie)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting movie: {e}",
        )


@router.patch(
    "/{movie_id}",
    status_code=status.HTTP_200_OK,
    summary="Update a movie by id",
    response_model=MovieResponse,
)
def update_movie_by_id(
    movie_id: str, movie_update: dict[str, Any], db: Session = Depends(get_db)
) -> MovieResponse:
    try:
        movie = db.execute(
            select(Movie).where(Movie.id == movie_id)
        ).scalar_one_or_none()
        if movie is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
            )
        for key, value in movie_update.items():
            setattr(movie, key, value)
        movie.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(movie)

        # Sync to Elasticsearch
        search_service = SearchService(db)
        search_service.sync_movie_to_elasticsearch(movie)

        return MovieResponse.model_validate(movie)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating movie: {e}",
        )
