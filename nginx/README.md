# Nginx Reverse Proxy Setup

This nginx configuration acts as a reverse proxy for all microservices, providing a single entry point for all API requests.

## Quick Start

### 1. Start all services with Docker Compose

```bash
# From the project root directory
docker-compose up -d
```

This will start:

- Backend services
- Databases
- Redis
- Elasticsearch
- **Nginx** (on port 80)

### 2. Access services through Nginx

Once running, you can access all services through nginx on port 80:

- **Frontend**: http://localhost/
- **Auth Service**: http://localhost/auth/
- **Booking Service**: http://localhost/booking/

### 3. API Documentation

Each service's API docs are available at:

- Auth: http://localhost/auth/docs
- Booking: http://localhost/booking/docs

### 4. Health Check

Check if nginx is running:

```bash
curl http://localhost/health
```

## Running Individual Services

If you want to run services individually (not through nginx):

- Auth Service: http://localhost:8000
- Booking Service: http://localhost:8003
- AI Agent RAG Service: http://localhost:8001

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Viewing Logs

```bash
# View nginx logs
docker logs nginx

# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f auth-service
docker-compose logs -f booking-service
```

## Troubleshooting

### Nginx can't connect to services

1. Check if services are running:

   ```bash
   docker-compose ps
   ```

2. Verify services are on the same network:

   ```bash
   docker network inspect fastapi-learning_microservices-network
   ```

3. Test service connectivity from nginx container:
   ```bash
   docker exec -it nginx sh
   # Inside container:
   wget -O- http://auth-service:8000/
   ```

### Port 80 already in use

If port 80 is already in use, change the nginx port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8080:80" # Use port 8080 instead
```

Then access via: http://localhost:8080

### Service not responding

1. Check service health:

   ```bash
   curl http://localhost/auth/
   curl http://localhost/booking/
   ```

2. Check nginx error logs:

   ```bash
   docker logs nginx
   ```

3. Verify nginx configuration:
   ```bash
   docker exec -it nginx nginx -t
   ```
