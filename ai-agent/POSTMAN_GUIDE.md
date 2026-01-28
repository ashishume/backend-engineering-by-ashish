# Postman Testing Guide

## Quick Start

Your AI Chat Agent API is now running on `http://localhost:8001`

## Method 1: Import Postman Collection (Recommended)

1. Open Postman
2. Click **Import** button (top left)
3. Select the file: `AI_Chat_Agent.postman_collection.json`
4. You'll see 8 pre-configured requests ready to use:
   - Health Check
   - Simple Chat
   - Chat with History
   - Chat with Different Model
   - Agent - Simple Task
   - Agent - Complex Calculation
   - Agent - Search Task
   - Agent - Multiple Tools

## Method 2: Manual Testing

### 1. Health Check

**Request:**

- Method: `GET`
- URL: `http://localhost:8001/`

**Expected Response:**

```json
{
  "status": "ok",
  "message": "AI Chat Agent API is running"
}
```

---

### 2. Simple Chat (No History)

**Request:**

- Method: `POST`
- URL: `http://localhost:8001/chat`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):

```json
{
  "message": "What is FastAPI?"
}
```

**Expected Response:**

```json
{
  "assistant_message": "FastAPI is a modern, fast web framework...",
  "conversation_history": [
    {
      "role": "user",
      "content": "What is FastAPI?"
    },
    {
      "role": "assistant",
      "content": "FastAPI is a modern, fast web framework..."
    }
  ]
}
```

---

### 3. Chat with Conversation History

**Request:**

- Method: `POST`
- URL: `http://localhost:8001/chat`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):

```json
{
  "message": "Can you give me an example?",
  "conversation_history": [
    {
      "role": "user",
      "content": "What is FastAPI?"
    },
    {
      "role": "assistant",
      "content": "FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints."
    }
  ]
}
```

**Expected Response:**
The AI will provide an example, understanding the context from the conversation history.

---

### 4. Using Different Models

**Request:**

- Method: `POST`
- URL: `http://localhost:8001/chat`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):

```json
{
  "message": "Tell me a joke",
  "model": "gpt-4o-mini"
}
```

Available models:

- `gpt-4o` (default) - Most capable
- `gpt-4o-mini` - Faster and cheaper
- `gpt-4-turbo` - Previous generation
- `gpt-3.5-turbo` - Fastest

---

## Autonomous Agent Endpoint

### 5. Agent - Simple Task

**Request:**

- Method: `POST`
- URL: `http://localhost:8001/agent`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):

```json
{
  "task": "What is 25 multiplied by 4, and what time is it now?"
}
```

**Expected Response:**

```json
{
  "result": "25 multiplied by 4 is 100. The current time is 2026-01-29 00:41:13.",
  "iterations_used": 2,
  "tools_used": ["calculate", "get_current_time"]
}
```

---

### 6. Agent - Complex Multi-Step Task

**Request:**

- Method: `POST`
- URL: `http://localhost:8001/agent`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):

```json
{
  "task": "Calculate the sum of 15 and 27, then multiply the result by 3. Also tell me what time it is.",
  "max_iterations": 15
}
```

The agent will:

1. Use the `calculate` tool to compute 15 + 27
2. Use the `calculate` tool again to multiply by 3
3. Use the `get_current_time` tool
4. Provide a complete answer

---

### 7. Agent - Search Task

**Request:**

- Method: `POST`
- URL: `http://localhost:8001/agent`
- Headers:
  - `Content-Type: application/json`
- Body (raw JSON):

```json
{
  "task": "Search for information about FastAPI and tell me what you find"
}
```

**Note:** The search tool currently returns mock results. In production, this would integrate with a real search API.

---

## Available Tools for Agent

The agent has access to these tools:

1. **calculate** - Perform mathematical calculations
   - Example: "2 + 2", "10 \* 5", "100 / 4"

2. **get_current_time** - Get current date and time
   - No parameters needed

3. **search_info** - Search for information (mock in current version)
   - Takes a search query as parameter

---

## Tips for Testing

### Chat Endpoint

1. **Maintain Conversation Context:**
   - Copy the `conversation_history` from the previous response
   - Include it in your next request to maintain context

2. **Test Error Handling:**
   - Try sending an empty message: `{"message": ""}`
   - Try invalid JSON to see validation errors

### Agent Endpoint

1. **Complex Tasks:**
   - The agent can break down complex tasks into steps
   - It will automatically use the right tools

2. **Monitor Iterations:**
   - Check `iterations_used` to see how many steps it took
   - Adjust `max_iterations` for complex tasks

3. **Tool Usage:**
   - The `tools_used` array shows which tools were called
   - Useful for debugging and understanding agent behavior

4. **Response Times:**
   - Agent tasks take longer than simple chat (3-10 seconds)
   - Each tool call adds to the response time

---

## Troubleshooting

### Server Not Running

```bash
cd ai-agent
python3 -m uvicorn main:app --reload --port 8001
```

### Connection Refused

- Make sure the server is running on port 8001
- Check if another service is using the port

### OpenAI API Errors

- Verify your API key in `.env` file
- Check your OpenAI account has credits
- Ensure you have access to the model you're requesting

### Agent Not Using Tools

- Make sure your task requires tool usage
- Try being more explicit: "Calculate 5 + 5 using the calculator"
- Check server logs for errors

---

## Interactive Documentation

Visit these URLs in your browser for interactive API testing:

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

Both provide a web interface to test the API without Postman!

---

## Example Agent Tasks to Try

1. **Math Problems:**
   - "What is 123 multiplied by 456?"
   - "Calculate (50 + 30) \* 2"

2. **Time-Based:**
   - "What time is it?"
   - "Tell me the current date and time"

3. **Combined Tasks:**
   - "Calculate 100 / 5 and tell me what time it is"
   - "Search for Python tutorials and calculate 7 \* 8"

4. **Multi-Step:**
   - "Add 25 and 75, then divide the result by 10"
   - "Calculate the sum of 10, 20, and 30, then multiply by 2"
