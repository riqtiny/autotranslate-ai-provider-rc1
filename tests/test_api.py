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
import random

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
def _is_translation(model: str) -> bool:
    return any(k in model for k in ("translategemma", "nllb", "t5gemma"))


def _infer_payload(model: str, **overrides) -> dict:
    """Build a request; translation models need lang codes and/or a prompt."""
    if "nllb" in model:  # NLLB uses FLORES-200 codes
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "source_lang": "eng_Latn",
            "target_lang": "fra_Latn",
            "max_tokens": 64,
            "temperature": 0.0,
        }
    elif "t5gemma" in model:  # text-to-text, instruct via the prompt
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "Translate to French: Hello, how are you?"}],
            "max_tokens": 64,
            "temperature": 0.0,
        }
    elif "translategemma" in model:  # ISO 639-1 codes
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


# --- translation: random language -> Indonesian (verbose) -------------------
# Run with `pytest tests/ -v -s` to see the printed steps.
# Each sample carries the codes for every translation family it can drive.
_SAMPLES = [
    # (label, text, iso, flores)
    ("en", "The weather is beautiful today.", "en", "eng_Latn"),
    ("fr", "Le chat dort sur le canapé.", "fr", "fra_Latn"),
    ("es", "Me gusta mucho la comida picante.", "es", "spa_Latn"),
    ("de", "Ich lerne seit zwei Jahren programmieren.", "de", "deu_Latn"),
]


def test_translate_random_to_indonesian(model):
    if not _is_translation(model):
        pytest.skip(f"'{model}' is not a translation model "
                    "(set CT2_TEST_MODEL to translategemma-4b-it / nllb-200-distilled-1.3b / t5gemma-2-4b-4b)")

    label, text, iso, flores = random.choice(_SAMPLES)
    print(f"\n[translate] {label} -> Indonesian  (model={model})")
    print(f"[translate] source: {text}")

    if "nllb" in model:           # FLORES-200 codes
        payload = _infer_payload(model, messages=[{"role": "user", "content": text}],
                                 source_lang=flores, target_lang="ind_Latn")
    elif "t5gemma" in model:      # instruct via prompt, no codes
        payload = _infer_payload(model, messages=[
            {"role": "user", "content": f"Translate to Indonesian: {text}"}])
    else:                          # translategemma, ISO 639-1
        payload = _infer_payload(model, messages=[{"role": "user", "content": text}],
                                 source_lang=iso, target_lang="id")
    print(f"[translate] POST /v1/chat/completions  {json.dumps(payload, ensure_ascii=False)}")

    r = _post("/v1/chat/completions", json=payload)
    print(f"[translate] status: {r.status_code}")
    if r.status_code != 200:
        # print the FULL error (pytest's skip reason truncates it)
        print(f"[translate] error body: {r.text}")
        pytest.skip(f"model '{model}' not converted/loadable (see body above)")

    body = r.json()
    translation = body["choices"][0]["message"]["content"]
    print(f"[translate] indonesian: {translation}")
    print(f"[translate] usage: {body['usage']}")

    assert translation.strip(), "empty translation"
    assert body["model"] == model
