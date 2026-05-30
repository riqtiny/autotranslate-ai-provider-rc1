"""OpenAI-compatible request/response models.

Only the subset of fields used by typical clients (openai-python, LangChain,
LiteLLM) is modeled. Unknown fields are ignored so clients can send extras.
"""
from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int = 0
    frequency_penalty: float = 0.0  # mapped onto repetition_penalty
    stream: bool = False

    model_config = {"extra": "ignore"}

    def repetition_penalty(self) -> float:
        # OpenAI frequency_penalty in [-2,2]; CT2 repetition_penalty ~[1,2].
        return 1.0 + max(0.0, self.frequency_penalty) * 0.5


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatChoice]
    usage: Usage


# --- streaming chunks ---
class DeltaMessage(BaseModel):
    role: str | None = None
    content: str | None = None


class ChatChunkChoice(BaseModel):
    index: int = 0
    delta: DeltaMessage
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatChunkChoice]


# --- /v1/models ---
class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "ctranslate2"


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelCard]
