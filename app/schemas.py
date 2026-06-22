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
    # Required only by translation models like translategemma (e.g. "en", "fr").
    source_lang: str | None = None
    target_lang: str | None = None

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


# --- /metrics/score ---
class MetricSegment(BaseModel):
    src: str  # source sentence (original language)
    mt: str  # machine translation / hypothesis
    ref: str  # gold reference translation


class MetricRequest(BaseModel):
    model: str | None = None  # optional label for the system being scored
    segments: list[MetricSegment]
    comet: bool = False  # opt-in: COMET is heavy and loaded lazily

    model_config = {"extra": "ignore"}


class MetricResponse(BaseModel):
    available: dict[str, bool]  # which backends are installed
    comet_model: str | None = None
    segments: list[dict]  # per-segment scores: {"bleu", "chrf", "comet"?}
    system: dict  # corpus/system scores: {"bleu", "chrf", "comet"?}
    errors: dict[str, str] = Field(default_factory=dict)


# --- /v1/models ---
class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "ctranslate2"


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelCard]
