from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field
from schemas import ChatRequest, ChatResponse, AgentRequest, AgentResponse, Message
from util import execute_tool

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI Chat Agent API",
    description="API for interacting with OpenAI chat models",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Define available tools for the agent
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform basic mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information on any topic. Use this to find recent news, facts, or information not in your training data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to look up on the web",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
]


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "AI Chat Agent API is running"}


@app.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    tags=["Chat"],
    summary="Send a message to the AI chat agent",
)
async def chat_agent(request: ChatRequest):
    """
    Send a message to the AI chat agent and get a response.

    - **message**: The user's message to send to the AI
    - **conversation_history**: Optional list of previous messages for context
    - **model**: OpenAI model to use (default: gpt-4o)

    Returns the AI's response and the updated conversation history.
    """
    try:
        # Convert Pydantic models to dict for OpenAI API
        conversation_history = [
            msg.model_dump() for msg in request.conversation_history
        ]

        # Add user message to history
        conversation_history.append({"role": "user", "content": request.message})

        # Call OpenAI API
        response = client.chat.completions.create(
            model=request.model,
            messages=conversation_history,
        )

        # Extract assistant's response
        assistant_message = response.choices[0].message.content

        # Add assistant message to history
        conversation_history.append({"role": "assistant", "content": assistant_message})

        return ChatResponse(
            assistant_message=assistant_message,
            conversation_history=[Message(**msg) for msg in conversation_history],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}",
        )


@app.post(
    "/agent",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    tags=["Agent"],
    summary="Run an autonomous agent to complete a task",
)
async def run_agent(request: AgentRequest):
    """
    Run an autonomous agent that can use tools to complete complex tasks.

    The agent will:
    - Break down the task into steps
    - Use available tools (calculate, get_current_time, web_search)
    - Iterate until the task is complete or max iterations reached

    - **task**: Description of the task to complete
    - **max_iterations**: Maximum number of iterations (default: 10)

    Returns the final result, number of iterations used, and tools called.
    """
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that breaks down tasks and uses tools to complete them.",
            },
            {"role": "user", "content": request.task},
        ]

        tools_used = []

        for i in range(request.max_iterations):
            response = client.chat.completions.create(
                model="gpt-4o", messages=messages, tools=tools
            )

            message = response.choices[0].message

            # Add assistant message to conversation
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": (
                        [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ]
                        if message.tool_calls
                        else None
                    ),
                }
            )

            if message.tool_calls:
                # Execute tools and add results to messages
                for tool_call in message.tool_calls:
                    tools_used.append(tool_call.function.name)
                    result = await execute_tool(tool_call)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
            else:
                # Agent is done
                return AgentResponse(
                    result=message.content or "Task completed",
                    iterations_used=i + 1,
                    tools_used=list(set(tools_used)),  # Remove duplicates
                )

        # Max iterations reached
        return AgentResponse(
            result=message.content or "Max iterations reached. Task may be incomplete.",
            iterations_used=request.max_iterations,
            tools_used=list(set(tools_used)),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing agent request: {str(e)}",
        )
