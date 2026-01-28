from pydantic import BaseModel, Field
from typing import List


# Pydantic models for request/response validation
class Message(BaseModel):
    """Single message in conversation"""

    role: str = Field(
        ..., description="Role of the message sender (user/assistant/system)"
    )
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""

    message: str = Field(
        ..., description="User message to send to the AI", min_length=1
    )
    conversation_history: List[Message] = Field(
        default_factory=list, description="Previous conversation history"
    )
    model: str = Field(default="gpt-4o", description="OpenAI model to use")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""

    assistant_message: str = Field(..., description="AI assistant's response")
    conversation_history: List[Message] = Field(
        ..., description="Updated conversation history"
    )


class AgentRequest(BaseModel):
    """Request model for agent endpoint"""

    task: str = Field(..., description="Task for the agent to complete", min_length=1)
    max_iterations: int = Field(
        default=10, description="Maximum number of iterations", ge=1, le=50
    )


class AgentResponse(BaseModel):
    """Response model for agent endpoint"""

    result: str = Field(..., description="Agent's final response")
    iterations_used: int = Field(..., description="Number of iterations used")
    tools_used: List[str] = Field(
        default_factory=list, description="List of tools used"
    )
