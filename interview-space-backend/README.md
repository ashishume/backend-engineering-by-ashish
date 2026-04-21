# Interview Space Backend

A clean FastAPI boilerplate using:

- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL (`asyncpg`)
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

## API Endpoints

- `GET /` - health check
- `POST /api/v1/users/` - create user
- `GET /api/v1/users/` - list users
