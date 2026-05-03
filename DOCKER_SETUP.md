# Docker Setup Guide

This guide explains how to run all FastAPI microservices using Docker and Docker Compose.

## Prerequisites

- Docker installed (version 20.10 or higher)
- Docker Compose installed (version 2.0 or higher)

## Services Overview

The application consists of multiple microservices, each with its own PostgreSQL database:

| Service         | Port | Database Port | Description                        |
| --------------- | ---- | ------------- | ---------------------------------- |
| auth-service    | 8000 | 5435          | Authentication and user management |
| booking-service | 8003 | 5436          | Movie theater booking system       |
| ai-agent        | 8001 | 5439          | RAG assistant service              |
| client          | 5173 | -             | React frontend (commented)         |

**Infrastructure Services**:

- Qdrant (Ports 6333/6334) - Vector database for RAG documents
- Elasticsearch (Port 9200) - Full-text search
- Nginx (Port 80) - Reverse proxy

## Quick Start

### 1. Start All Services

From the project root directory, run:

```bash
docker-compose up -d
```

This command will:

- Build Docker images for all services
- Create and start all containers
- Set up the network for inter-service communication
- Create persistent volumes for databases

### 2. View Running Containers

```bash
docker-compose ps
```

### 3. View Logs

View logs for all services:

```bash
docker-compose logs -f
```

View logs for a specific service:

```bash
docker-compose logs -f auth-service
docker-compose logs -f booking-service
docker-compose logs -f ai-agent
docker-compose logs -f qdrant
docker-compose logs -f elasticsearch
```

### 4. Stop All Services

```bash
docker-compose down
```

To stop and remove volumes (database data):

```bash
docker-compose down -v
```

## Access Services

Once all services are running, you can access them at:

- **Auth Service**: http://localhost:8000

  - API Docs: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc

- **Booking Service**: http://localhost:8003

  - API Docs: http://localhost:8003/docs
  - ReDoc: http://localhost:8003/redoc

- **AI Agent RAG Service**: http://localhost:8001

  - API Docs: http://localhost:8001/docs
  - ReDoc: http://localhost:8001/redoc

- **Client (React Frontend)**: http://localhost:5173 (if enabled)

- **Qdrant**: http://localhost:6333

- **Nginx Reverse Proxy**: http://localhost:80

## Database Access

You can connect to the PostgreSQL databases using these credentials:

### Auth Service Database

```bash
docker exec -it auth-db psql -U postgres -d auth_service
```

- Host: localhost
- Port: 5435
- Database: auth_service
- User: postgres
- Password: admin

### Booking Service Database

```bash
docker exec -it booking-db psql -U postgres -d booking_service
```

- Host: localhost
- Port: 5436
- Database: booking_service
- User: postgres
- Password: admin

### AI Agent Database

```bash
docker exec -it ai-agent-db psql -U postgres -d ai_agent
```

- Host: localhost
- Port: 5439
- Database: ai_agent
- User: postgres
- Password: admin

## Common Docker Commands

### Build Services

Rebuild all services:

```bash
docker-compose build
```

Rebuild a specific service:

```bash
docker-compose build auth-service
```

Rebuild without cache:

```bash
docker-compose build --no-cache
```

### Start/Stop Services

Start all services:

```bash
docker-compose up -d
```

Start specific services:

```bash
docker-compose up -d auth-service booking-service
```

Stop all services:

```bash
docker-compose stop
```

Stop specific service:

```bash
docker-compose stop auth-service
```

Restart services:

```bash
docker-compose restart
```

### Execute Commands in Containers

Open a shell in a container:

```bash
docker-compose exec auth-service sh
```

Run a command in a container:

```bash
docker-compose exec auth-service python -c "print('Hello')"
```

### Database Migrations

Run Alembic migrations for auth-service:

```bash
docker-compose exec auth-service alembic upgrade head
```

Run Alembic migrations for booking-service:

```bash
docker-compose exec booking-service alembic upgrade head
```

Create a new migration:

```bash
docker-compose exec auth-service alembic revision --autogenerate -m "description"
```

## Troubleshooting

### Service won't start

1. Check logs:

```bash
docker-compose logs auth-service
```

2. Ensure no port conflicts:

```bash
lsof -i :8000  # Check if port is already in use
```

3. Rebuild the service:

```bash
docker-compose build auth-service
docker-compose up -d auth-service
```

### Database connection issues

1. Check if database is healthy:

```bash
docker-compose ps
```

2. Wait for database to be ready (healthcheck):

```bash
docker-compose logs auth-db
```

3. Test database connection:

```bash
docker-compose exec auth-db psql -U postgres -d auth_service
```

### Clear all data and restart

```bash
# Stop all services and remove volumes
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Start fresh
docker-compose up -d --build
```

## Development Mode

The services are configured with volume mounts, so code changes will automatically reload:

- Edit your Python files locally
- The changes are synced to the container
- Uvicorn will automatically reload the application

## Production Considerations

For production deployment, consider:

1. **Remove `--reload` flag** from Dockerfiles (CMD line)
2. **Use environment files** instead of hardcoded values
3. **Set strong passwords** for databases
4. **Use secrets management** for sensitive data
5. **Configure proper logging** and monitoring
6. **Set resource limits** in docker-compose.yml
7. **Use Docker swarm or Kubernetes** for orchestration
8. **Implement health checks** for load balancers
9. **Use multi-stage builds** to reduce image size
10. **Scan images** for security vulnerabilities

## Environment Variables

Each service can be configured using environment variables. See the `env.example` files in each service directory:

- `auth-service/env.example`
- `booking-service/` (check service-specific configuration)
- `ai-agent/` (check service-specific configuration)

## Network Configuration

All services are connected to a custom bridge network called `microservices-network`. This allows services to communicate with each other using their service names as hostnames.

Examples:

- From booking-service, you can reach auth-service at `http://auth-service:8000`
- From booking-service, you can reach Elasticsearch at `http://elasticsearch:9200`
- From ai-agent, you can reach Qdrant at `http://qdrant:6333`

## Volume Management

Persistent volumes are created for each database and service:

- `auth-db-data`: Auth service database data
- `booking-db-data`: Booking service database data
- `ai-agent-db-data`: AI agent database data
- `qdrant-data`: Qdrant vector storage
- `elasticsearch-data`: Elasticsearch index data

To backup a database:

```bash
docker-compose exec auth-db pg_dump -U postgres auth_service > backup.sql
```

To restore a database:

```bash
cat backup.sql | docker-compose exec -T auth-db psql -U postgres auth_service
```

## Support

For issues or questions, please refer to the individual service README files or check the application logs.
