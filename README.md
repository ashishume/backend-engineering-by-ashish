# FastAPI Microservices Project

## 📋 Project Overview

A **comprehensive microservices-based application** built with FastAPI, demonstrating modern backend architecture with independent services communicating via HTTP/REST APIs and a React frontend. Features authentication, booking systems, RAG document chat, and supporting infrastructure.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         React Client (TypeScript + Tailwind CSS)            │
│                    Port: 5173 (via Nginx:80)                │
└────────┬──────────────────────┬─────────────────────────────┘
         │                      │
         ▼                      ▼
   ┌──────────┐          ┌──────────┐
   │   Auth   │          │ Booking  │
   │ Service  │          │ Service  │
   │ Port:8000│          │Port: 8003│
   └─────┬────┘          └─────┬────┘
         │                    │
         ▼                    ▼
   ┌──────────┐          ┌──────────┐
   │ auth_db  │          │booking_db│
   │Port:5435 │          │Port:5436 │
   └──────────┘          └─────┬────┘
                               │
                               ▼
                       ┌──────────────┐
                       │ Elasticsearch │
                       │  Port: 9200   │
                       └──────────────┘
```

---

## 🏗️ Services Architecture

### 1. Auth Service (Port 8000) ✅ Active

**Purpose**: Central authentication and user management

**Database**: `auth_service` on PostgreSQL (Port 5435)

**Features**:

- User registration and authentication
- JWT token generation/validation (HTTP-only cookies)
- Password hashing: SHA-256 pre-hash + bcrypt
- Role-based access control (SUPER_ADMIN, ADMIN, USER, MODERATOR)

**API Endpoints**:

- `POST /auth/` - User registration
- `POST /auth/login` - User login (sets cookie)
- `POST /auth/logout` - User logout

**Tech Stack**: FastAPI, SQLAlchemy, Alembic, python-jose, passlib+bcrypt, PostgreSQL

---

### 2. Booking Service (Port 8003) ✅ Active

**Purpose**: Movie theater booking system with Elasticsearch integration

**Database**: `booking_service` on PostgreSQL (Port 5436)

**Features**:

- Theater, movie, showing, and seat management
- Booking creation with seat availability validation
- Full-text search using Elasticsearch (movies, theaters, showings, bookings)
- Web scraping for upcoming IPOs (optional)

**Key Tables**: `theaters`, `movies`, `showings`, `seats`, `bookings`, `booking_seats`

**API Endpoints**:

- `POST/GET /theaters/`, `/movies/`, `/showings/`, `/seats/`, `/bookings/`
- `GET /search/?query={query}` - Elasticsearch multi-index search
- `POST /scrap/` - Scrape upcoming IPOs

**Tech Stack**: FastAPI, SQLAlchemy, PostgreSQL, Elasticsearch 8.11.0, Playwright (optional)

---

### 3. AI Agent RAG Service (Port 8001) ✅ Active

**Purpose**: Document ingestion and conversational RAG assistant

**Database**: `ai_agent` on PostgreSQL (Port 5439) with Qdrant vector storage

**Features**:

- Upload, list, and delete RAG documents
- Chat over indexed documents
- Thread and message persistence
- Qdrant-backed vector search

**API Endpoints**:

- `POST /rag/documents` - Upload a document
- `GET /rag/documents` - List uploaded documents
- `DELETE /rag/documents/{document_id}` - Delete a document
- `POST /rag/chat` - Chat with the assistant

**Tech Stack**: FastAPI, PostgreSQL, Qdrant, OpenRouter, LlamaIndex/LangChain components

---

### 4. Client (React Frontend) ✅ Active

**Purpose**: Modern React frontend for interacting with all microservices

**Port**: 5173 (accessible via Nginx on port 80)

**Features**: TypeScript, React Router, Axios, Tailwind CSS, Vite, Context API

**Tech Stack**: React 19.2.0, TypeScript 5.9.3, Vite 7.2.2, Tailwind CSS 4.1.17

---

### 5. Nginx Reverse Proxy ✅ Active

**Purpose**: Routes requests to appropriate services

**Port**: 80

**Configuration**: Routes `/auth/*` to auth-service, `/booking/*` to booking-service, `/` to client

---

## 🔐 Authentication & Security

### JWT Token Authentication

- **Algorithm**: HS256
- **Expiration**: 60 minutes (configurable)
- **Storage**: HTTP-only cookie (`access_token`)
- **Cookie Config**: httponly, secure (HTTPS in production), samesite: lax

### Password Security

1. SHA-256 pre-hashing (handles passwords > 72 bytes)
2. Bcrypt hashing (industry standard, with salt)
3. Automatic deprecation handling via passlib

### CORS Configuration

- Allow Origins: "\*" (development) - restrict in production
- Allow Credentials: True
- Allow Methods/Headers: All

---

## 🛠️ Technology Stack

**Core**: FastAPI 0.120.1, Python 3.14, Uvicorn 0.38.0

**Database**: PostgreSQL 16, SQLAlchemy 2.0.23, Alembic 1.13.1, psycopg2-binary 2.9.11

**Auth**: python-jose 3.3.0, passlib 1.7.4, bcrypt 4.1.2

**Validation**: Pydantic 2.12.3

**Infrastructure**: Docker & Docker Compose, Redis 7-alpine, Elasticsearch 8.11.0, Nginx

**Frontend**: React 19.2.0, TypeScript 5.9.3, Vite 7.2.2, Tailwind CSS 4.1.17

---

## 🔄 Inter-Service Communication

**HTTP/REST**: Async httpx client, JWT cookie forwarding, 10s timeout

**Search**: Booking Service → Elasticsearch (full-text search across multiple indices)

**Vector Search**: AI Agent → Qdrant

**Service Discovery**:

- Docker: `http://auth-service:8000`, `http://booking-service:8003`, `http://ai-agent:8001`
- Local: `http://localhost:8000`, `http://localhost:8003`, `http://localhost:8001`

---

## 🐳 Docker Configuration

### Active Services

```yaml
✅ auth-service + auth-db (PostgreSQL:5435)
✅ booking-service + booking-db (PostgreSQL:5436)
✅ client (React frontend:5173)
✅ ai-agent + ai-agent-db (PostgreSQL:5439)
✅ qdrant (Vector database:6333/6334)
```

**Networks**: `microservices-network` (bridge driver)

**Volumes**: Persistent storage for active databases and Qdrant

**Health Checks**: All databases include health checks

**Commands**:

```bash
docker-compose up -d          # Start all services
docker-compose logs -f        # View logs
docker-compose down           # Stop services
docker-compose down -v        # Stop and remove volumes
```

---

## 📊 Database Migrations (Alembic)

All services use Alembic for schema management.

**Common Commands**:

```bash
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback
alembic history                                   # View history
```

---

## 🚀 Quick Start

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

Access:

- Frontend: http://localhost (via Nginx)
- Auth Service: http://localhost:8000
- Booking Service: http://localhost:8003
- AI Agent: http://localhost:8001
- API Docs: http://localhost:8000/docs, http://localhost:8003/docs, http://localhost:8001/docs

### Local Development

```bash
# Auth Service
cd auth-service && uvicorn main:app --reload --port 8000

# Booking Service
cd booking-service && uvicorn main:app --reload --port 8003

# Client
cd client && npm run dev
```

---

## 🏗️ System Design Implementations

The `backend_system_design/` folder contains **educational system design implementations** using only Python standard library.

### 1. Movie Booking System (`movie_booking_design.py`)

**Features**: Seat locking (5min default), payment strategies, booking confirmation/cancellation, thread-safe operations

**Patterns**: Strategy Pattern (PaymentStrategy), Repository Pattern, Lock/RLock for concurrency

**Key Classes**: `User`, `Movie`, `Theater`, `Showings`, `Seats`, `Bookings`, `BookingService`

---

### 2. Parking System (`parking_system_design.py`)

**Features**: Multi-floor architecture, vehicle types (Car/Truck/Bike), spot matching, hourly pricing, ticket system

**Patterns**: Strategy Pattern (PricingStrategy), Abstract Factory (ParkingSpot hierarchy)

**Key Classes**: `Vehicle`, `ParkingSpot` (abstract), `ParkingFloor`, `ParkingLot`, `ParkingTicket`, `Gate`

---

### 3. Uber/Ride-Sharing System (`uber_riding_design.py`)

**Features**: Driver-rider matching, ride lifecycle, distance-based pricing, driver status management

**Patterns**: Service Layer Pattern, Strategy Pattern (PricingService)

**Key Classes**: `Rider`, `Driver`, `Ride`, `RideService`, `DriverService`, `MatchingService`, `PricingService`

**Common Principles**: OOP design, thread-safe operations, design patterns (Strategy, Service Layer, Repository), standard library only

---

## 🎯 Key Features & Patterns

1. **Microservices Architecture** - Service isolation, independent databases, autonomous deployment
2. **Repository Pattern** - Database access abstraction
3. **Service Layer Pattern** - Business logic separation
4. **Middleware Pattern** - CORS, authentication
5. **Lifespan Events** - Database initialization, Elasticsearch index creation, Redis connection management
6. **RAG Pipeline** - Document ingestion, embeddings, vector search, and chat
7. **Error Handling** - Comprehensive exception management with logging

---

## 📖 API Documentation

All services provide auto-generated documentation:

- **Swagger UI**: `http://localhost:{port}/docs`
- **ReDoc**: `http://localhost:{port}/redoc`

### Example Flow

1. **Register**: `POST /auth/` with `{"email": "...", "name": "...", "password": "..."}`
2. **Login**: `POST /auth/login` - sets HTTP-only cookie with JWT token
3. **Create Booking**: `POST /bookings/` with cookie - creates booking with seat locking
4. **Search**: `GET /search/?query=action` - Elasticsearch multi-index search

---

## 🔍 Project Structure

```
backend-engineering-by-ashish/
├── auth-service/          # Auth service (✅ Active)
├── booking-service/       # Booking service (✅ Active)
├── ai-agent/              # RAG assistant service (✅ Active)
├── client/                # React frontend (✅ Active)
├── nginx/                 # Reverse proxy config (✅ Active)
├── backend_system_design/ # System design implementations
│   ├── movie_booking_design.py
│   ├── parking_system_design.py
│   └── uber_riding_design.py
├── docker-compose.yml     # Multi-service orchestration
└── README.md              # This file
```

---

## 🎓 Learning Objectives

✅ Microservices Architecture | ✅ RESTful API Design | ✅ JWT Authentication  
✅ Database Relationships | ✅ Inter-Service Communication | ✅ Docker Containerization  
✅ Database Migrations | ✅ Error Handling & Logging | ✅ API Documentation  
✅ Dependency Injection | ✅ Type Safety (Pydantic) | ✅ Async Programming  
✅ Elasticsearch Integration | ✅ Vector Search | ✅ RAG Workflows  
✅ Repository & Service Layer Patterns | ✅ System Design Patterns  
✅ Concurrency Handling | ✅ Real-World System Design

---

## 🚧 Known Limitations

- No circuit breaker pattern
- No message queue
- Limited caching
- Basic logging (no centralized aggregation)
- No monitoring/metrics collection
- No service mesh or API gateway

---

## 🎉 Summary

**Active Services**: Auth Service, Booking Service, AI Agent, Client (React), Qdrant

**Key Features**:

- Independent backend services for auth, booking, and RAG
- JWT-based authentication with secure password hashing
- Elasticsearch full-text search
- Qdrant vector search for document chat
- React frontend with TypeScript
- Docker containerization
- 3 system design implementations (Movie Booking, Parking, Uber/Ride-Sharing)

**Perfect for**: Learning microservices, building MVPs, understanding distributed systems, system design patterns, or as a template for larger projects.

---

**Last Updated**: January 2025  
**Project Status**: Active Development  
**License**: MIT
