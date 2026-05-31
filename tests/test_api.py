"""End-to-end API tests against a *running* server.

Point them at any base URL (localhost or your Cloudflare tunnel):

    export CT2_TEST_BASE_URL=http://localhost:8000
    export CT2_TEST_API_KEY=...        # only if the server enforces a key
    export CT2_TEST_MODEL=qwen3-4b     # defaults to the first /v1/models entry
    pytest tests/ -v

Generation tests auto-skip if no model is loaded/available, so the suite still
validates the API surface even before a model is converted.
"""
from __future__ import annotations

import json
import os

import pytest
import requests

BASE = os.environ.get("CT2_TEST_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("CT2_TEST_API_KEY", "")
TIMEOUT = float(os.environ.get("CT2_TEST_TIMEOUT", "120"))
HEADERS = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}


def _get(path: str, **kw):
    return requests.get(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT, **kw)


def _post(path: str, **kw):
    return requests.post(f"{BASE}{path}", headers=HEADERS, timeout=TIMEOUT, **kw)


@pytest.fixture(scope="session")
def reachable():
    try:
        _get("/admin/status")
    except requests.exceptions.RequestException as e:
        pytest.skip(f"server not reachable at {BASE}: {e}")


@pytest.fixture(scope="session")
def model(reachable) -> str:
    if env := os.environ.get("CT2_TEST_MODEL"):
        return env
    data = _get("/v1/models").json()["data"]
    if not data:
        pytest.skip("no supported models advertised by /v1/models")
    return data[0]["id"]


# --- surface (no inference needed) ------------------------------------------
def test_list_models(reachable):
    r = _get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    assert all(m["object"] == "model" for m in body["data"])


def test_admin_status(reachable):
    body = _get("/admin/status").json()
    assert "loaded_model" in body and "models" in body and "vram" in body


def test_admin_vram(reachable):
    r = _get("/admin/vram")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)  # {} when no GPU, populated otherwise


def test_unknown_model_is_400(reachable):
    r = _post("/v1/chat/completions", json={
        "model": "does-not-exist",
        "messages": [{"role": "user", "content": "hi"}],
    })
    assert r.status_code == 400


@pytest.mark.skipif(not API_KEY, reason="no API key configured")
def test_auth_rejected_without_key(reachable):
    r = requests.get(f"{BASE}/v1/models", timeout=TIMEOUT)  # no auth header
    assert r.status_code == 401


# --- inference (needs a usable model) ---------------------------------------
def _infer_payload(model: str, **overrides) -> dict:
    """Build a request; translation models need lang codes + a translate prompt."""
    if "translategemma" in model:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "source_lang": "en",
            "target_lang": "fr",
            "max_tokens": 32,
            "temperature": 0.0,
        }
    else:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with the single word: pong"}],
            "max_tokens": 16,
            "temperature": 0.0,
        }
    body.update(overrides)
    return body


def test_chat_completion(model):
    r = _post("/v1/chat/completions", json=_infer_payload(model))
    if r.status_code == 400:
        pytest.skip(f"model '{model}' not converted/loadable: {r.text}")
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["model"]
    content = body["choices"][0]["message"]["content"]
    assert isinstance(content, str) and content.strip()
    u = body["usage"]
    assert u["total_tokens"] == u["prompt_tokens"] + u["completion_tokens"]


def test_chat_completion_stream(model):
    r = _post("/v1/chat/completions",
              json=_infer_payload(model, stream=True), stream=True)
    if r.status_code == 400:
        pytest.skip(f"model '{model}' not converted/loadable: {r.text}")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")

    chunks, saw_done, got_content = 0, False, False
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload == "[DONE]":
            saw_done = True
            break
        obj = json.loads(payload)
        if "error" in obj:  # streaming errors arrive in-band (200 already sent)
            pytest.skip(f"model '{model}' not loadable: {obj['error']['message']}")
        chunks += 1
        delta = obj["choices"][0]["delta"]
        if delta.get("content"):
            got_content = True
    assert chunks > 0 and saw_done and got_content
