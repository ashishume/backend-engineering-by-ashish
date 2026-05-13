# Interview Space Backend

A clean FastAPI boilerplate using:

- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL (`asyncpg`)
- Redis (`redis-py`, async client)
- Pydantic Settings

## Quick Start

1. Create and activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create environment file:

```bash
cp .env.example .env
```

4. Run the API:

```bash
uvicorn app.main:app --reload
```

Redis defaults to `redis://localhost:6379/0`. Override it with `REDIS_URL` in `.env` if your Redis server runs somewhere else.

## API Endpoints

- `GET /` - health check
- `POST /api/v1/users/` - create user
- `GET /api/v1/users/` - list users
