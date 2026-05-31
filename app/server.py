"""FastAPI app: OpenAI-compatible inference + admin (switch, vram, convert)."""
from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from .config import settings
from .converter import convert
from .manager import manager, vram_stats
from .schemas import (
    ChatChoice,
    ChatChunkChoice,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    DeltaMessage,
    ModelCard,
    ModelList,
    Usage,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.default_model:
        try:
            manager.load(settings.default_model)
        except Exception as e:  # don't crash boot; report on /admin/status
            print(f"[startup] could not load default model: {e}")
    yield
    manager.unload()


app = FastAPI(title="CTranslate2 OpenAI-compatible Provider", lifespan=lifespan)


def require_key(authorization: str | None = Header(default=None)) -> None:
    if not settings.api_key:
        return
    if authorization != f"Bearer {settings.api_key}":
        raise HTTPException(status_code=401, detail="Invalid API key")


# --- OpenAI-compatible -------------------------------------------------------
@app.get("/v1/models", response_model=ModelList)
def list_models(_: None = Depends(require_key)) -> ModelList:
    return ModelList(
        data=[ModelCard(id=s.key) for s in settings.registry.values() if s.supported]
    )


@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest, _: None = Depends(require_key)):
    messages = [m.model_dump() for m in req.messages]
    kwargs = dict(
        model=req.model,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        top_p=req.top_p,
        top_k=req.top_k,
        repetition_penalty=req.repetition_penalty(),
        source_lang=req.source_lang,
        target_lang=req.target_lang,
    )
    try:
        if req.stream:
            return StreamingResponse(
                _stream_chunks(req, messages, kwargs),
                media_type="text/event-stream",
            )
        result = manager.generate(messages, **kwargs)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ChatCompletionResponse(
        model=result["model"],
        choices=[ChatChoice(message=ChatMessage(role="assistant", content=result["text"]))],
        usage=Usage(
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            total_tokens=result["prompt_tokens"] + result["completion_tokens"],
        ),
    )


def _stream_chunks(req, messages, kwargs):
    cid = f"chatcmpl-{int(time.time()*1000)}"
    model = req.model

    def chunk(choice: ChatChunkChoice) -> str:
        payload = ChatCompletionChunk(id=cid, model=model, choices=[choice])
        return f"data: {payload.model_dump_json()}\n\n"

    yield chunk(ChatChunkChoice(delta=DeltaMessage(role="assistant")))
    try:
        for delta in manager.stream(messages, **kwargs):
            yield chunk(ChatChunkChoice(delta=DeltaMessage(content=delta)))
    except Exception as e:  # never crash the stream; report in-band then close
        err = {"error": {"message": str(e), "type": "invalid_request_error"}}
        yield f"data: {json.dumps(err)}\n\n"
    yield chunk(ChatChunkChoice(delta=DeltaMessage(), finish_reason="stop"))
    yield "data: [DONE]\n\n"


# --- admin -------------------------------------------------------------------
@app.get("/admin/status")
def status(_: None = Depends(require_key)) -> dict:
    return manager.status()


@app.get("/admin/vram")
def vram(_: None = Depends(require_key)) -> dict:
    return vram_stats()


@app.post("/admin/switch/{key}")
def switch_model(key: str, _: None = Depends(require_key)) -> dict:
    try:
        manager.switch(key)
    except (KeyError, ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"loaded_model": manager.current_key, "vram": vram_stats()}


@app.post("/admin/unload")
def unload_model(_: None = Depends(require_key)) -> dict:
    manager.unload()
    return {"loaded_model": None, "vram": vram_stats()}


@app.post("/admin/convert/{key}")
def convert_model(key: str, force: bool = False, _: None = Depends(require_key)) -> dict:
    try:
        out = convert(key, force=force)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"key": key, "output_dir": str(out), "converted": True}
