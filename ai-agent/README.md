# RAG Assistant API

A FastAPI RAG service using OpenRouter for LLM/embedding calls, Qdrant for vector search, and LlamaIndex Memory for token-aware session chat memory.

## Features

- Document upload and indexing for PDF, TXT, and MD files
- Qdrant vector storage with cosine retrieval
- OpenRouter chat completions and embeddings
- LlamaIndex session memory keyed by `session_id`
- RAG answers with source snippets
- General answers when retrieval is unrelated
- CORS enabled for frontend integration
- Type-safe request/response validation with Pydantic

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenRouter API key:

```bash
cp .env.example .env
# Edit .env and add OPENROUTER_API_KEY
```

3. Start Qdrant:

```bash
docker run -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

4. Start Postgres for persistent thread memory:

```bash
docker run -p 5439:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=admin \
  -e POSTGRES_DB=ai_agent \
  -v ai_agent_db:/var/lib/postgresql/data \
  postgres:16-alpine
```

5. Run the server:

```bash
python3 -m uvicorn main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`

## API Endpoints

### Upload Document

**POST** `/rag/documents`

Multipart form field: `file`.

### List Documents

**GET** `/rag/documents`

### Delete Document

**DELETE** `/rag/documents/{document_id}`

### Chat

**POST** `/rag/chat`

**Request Body:**

```json
{
  "thread_id": "thread-id",
  "client_id": "browser-client-id",
  "message": "What does the uploaded document say about indexing?",
  "top_k": 6
}
```

**Response:**

```json
{
  "answer": "The document explains...",
  "mode": "rag",
  "sources": [
    {
      "document_id": "uuid",
      "filename": "notes.pdf",
      "chunk_index": 0,
      "text": "Source text...",
      "score": 0.82
    }
  ],
  "session_id": "thread-id",
  "thread_id": "thread-id"
}
```

### Threads And Persistent Memory

**POST** `/rag/threads`

```json
{
  "client_id": "browser-client-id",
  "title": "New chat"
}
```

**GET** `/rag/threads?client_id=browser-client-id`

**GET** `/rag/threads/{thread_id}/messages`

Thread turns are persisted in Postgres tables:

- `chat_threads`
- `chat_messages`
- `thread_memories`

You can inspect these tables in pgAdmin by connecting to `localhost:5439`,
database `ai_agent`, user `postgres`, password `admin`.

## Interactive API Documentation

Once the server is running, visit:

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Environment Variables

- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `CHAT_MODEL`: Default `openai/gpt-4o-mini`
- `EMBEDDING_MODEL`: Default `openai/text-embedding-3-small`
- `QDRANT_URL`: Default `http://localhost:6333`
- `QDRANT_COLLECTION`: Default `rag_documents`
- `MEMORY_TOKEN_LIMIT`: Default `6000`
- `POSTGRES_HOST`: Default `localhost`
- `POSTGRES_PORT`: Default `5439`
- `POSTGRES_DB`: Default `ai_agent`

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `422`: Validation error (invalid request body)
- `500`: Internal server error

Error responses include a `detail` field with more information.
