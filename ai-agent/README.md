# AI Chat Agent API

A FastAPI-based REST API for interacting with OpenAI's chat models.

## Features

- RESTful API endpoints for chat interactions
- **Autonomous agent with tool-calling capabilities**
- **Real web search integration** (DuckDuckGo + Tavily)
- Conversation history management
- Support for multiple OpenAI models
- Built-in tools: calculator, time, web search
- CORS enabled for frontend integration
- Type-safe request/response validation with Pydantic
- Comprehensive API documentation with Swagger UI

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

3. Run the server:

```bash
python3 -m uvicorn main:app --reload --port 8001
```

The API will be available at `http://localhost:8001`

## API Endpoints

### Health Check

**GET** `/`

Returns the API status.

**Response:**

```json
{
  "status": "ok",
  "message": "AI Chat Agent API is running"
}
```

### Chat with AI

**POST** `/chat`

Send a message to the AI and get a response.

### Autonomous Agent

**POST** `/agent`

Run an autonomous agent that can use tools to complete complex tasks.

**Request Body:**

```json
{
  "message": "Hello, how are you?",
  "conversation_history": [],
  "model": "gpt-4o"
}
```

**Response:**

```json
{
  "assistant_message": "Hello! I'm doing well, thank you for asking...",
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    },
    {
      "role": "assistant",
      "content": "Hello! I'm doing well, thank you for asking..."
    }
  ]
}
```

## Testing with Postman

### Import Collection

Import `AI_Chat_Agent.postman_collection.json` for 8 pre-configured requests.

### Manual Testing

1. **Health Check:**
   - Method: GET
   - URL: `http://localhost:8001/`

2. **Chat Request (Simple):**
   - Method: POST
   - URL: `http://localhost:8001/chat`
   - Headers: `Content-Type: application/json`
   - Body (raw JSON):

   ```json
   {
     "message": "What is FastAPI?"
   }
   ```

3. **Chat Request (With History):**
   - Method: POST
   - URL: `http://localhost:8001/chat`
   - Headers: `Content-Type: application/json`
   - Body (raw JSON):

   ```json
   {
     "message": "Can you explain more about that?",
     "conversation_history": [
       {
         "role": "user",
         "content": "What is FastAPI?"
       },
       {
         "role": "assistant",
         "content": "FastAPI is a modern, fast web framework for building APIs with Python..."
       }
     ],
     "model": "gpt-4o"
   }
   ```

4. **Agent Request (Autonomous Task):**
   - Method: POST
   - URL: `http://localhost:8001/agent`
   - Headers: `Content-Type: application/json`
   - Body (raw JSON):

   ```json
   {
     "task": "What is 25 multiplied by 4, and what time is it now?",
     "max_iterations": 10
   }
   ```

   The agent will automatically use tools (calculate, get_current_time) to complete the task.

## Interactive API Documentation

Once the server is running, visit:

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `TAVILY_API_KEY`: Your Tavily API key (optional, for better web search results)
  - Get free API key at https://tavily.com/
  - If not provided, DuckDuckGo will be used (free, no API key needed)

## Available Models

- `gpt-4o` (default): Most capable model
- `gpt-4o-mini`: Faster and cheaper alternative
- `gpt-4-turbo`: Previous generation turbo model
- `gpt-3.5-turbo`: Fastest and most cost-effective

## Agent Tools

The autonomous agent has access to these tools:

1. **calculate** - Perform mathematical calculations
   - Example: "2 + 2", "10 \* 5", "100 / 4"

2. **get_current_time** - Get current date and time
   - Returns formatted timestamp

3. **web_search** - Search the web for real-time information
   - Uses DuckDuckGo (free, no API key) or Tavily (better results, requires free API key)
   - Perfect for current news, facts, research
   - See `WEB_SEARCH_GUIDE.md` for detailed usage

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `422`: Validation error (invalid request body)
- `500`: Internal server error

Error responses include a `detail` field with more information.
