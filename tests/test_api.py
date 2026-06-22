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
import time

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


# What each leaderboard metric measures — printed by the benchmark tests so a
# `-s` run explains the numbers, not just emits them.
_METRIC_INFO = {
    "bleu": "BLEU / SacreBLEU: n-gram precision overlap vs the reference (0-100). "
    "SacreBLEU is the standardized, reproducible implementation.",
    "chrf": "ChrF++: character n-gram F-score plus word bigrams; robust on short "
    "sentences and rich morphology (0-100).",
    "comet": "COMET: neural metric (XLM-R) trained on human ratings; scores meaning "
    "from source + hypothesis + reference (~0-1).",
}


def _resource_line(status: dict) -> str:
    """Human-readable memory usage, picking GPU VRAM or CPU RAM by mode.

    /admin/vram is empty ({}) when there's no CUDA, so a populated vram block
    means we're on GPU; otherwise report system RAM + this process's RSS.
    """
    device = status.get("device", "?")
    vram = status.get("vram") or {}
    ram = status.get("ram") or {}
    if vram.get("used_mib") is not None:
        return (
            f"GPU mode [{vram.get('device', device)}]: "
            f"VRAM {vram['used_mib']}/{vram.get('total_mib')} MiB used"
        )
    return (
        f"CPU mode [{device}]: RAM {ram.get('used_mib')}/{ram.get('total_mib')} MiB "
        f"used, process RSS {ram.get('process_rss_mib')} MiB"
    )


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
    r = _post(
        "/v1/chat/completions",
        json={
            "model": "does-not-exist",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert r.status_code == 400


@pytest.mark.skipif(not API_KEY, reason="no API key configured")
def test_auth_rejected_without_key(reachable):
    r = requests.get(f"{BASE}/v1/models", timeout=TIMEOUT)  # no auth header
    assert r.status_code == 401


# --- inference (needs a usable model) ---------------------------------------
def _is_translation(model: str) -> bool:
    return any(k in model for k in ("translategemma", "nllb"))


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
            "messages": [
                {"role": "user", "content": "Reply with the single word: pong"}
            ],
            "max_tokens": 16,
            "temperature": 0.0,
        }
    body.update(overrides)
    return body


def test_chat_completion(model):
    t0 = time.perf_counter()
    r = _post("/v1/chat/completions", json=_infer_payload(model))
    elapsed = time.perf_counter() - t0
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

    # Throughput + device-aware memory (run with -s to see these).
    tps = u["completion_tokens"] / elapsed if elapsed > 0 else 0.0
    print(
        f"\n[infer] {model}: {u['completion_tokens']} tokens in {elapsed:.2f}s "
        f"= {tps:.1f} tok/s"
    )
    print(f"[infer] {_resource_line(_get('/admin/status').json())}")
    assert tps >= 0


def test_chat_completion_stream(model):
    r = _post(
        "/v1/chat/completions", json=_infer_payload(model, stream=True), stream=True
    )
    if r.status_code == 400:
        pytest.skip(f"model '{model}' not converted/loadable: {r.text}")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")

    chunks, saw_done, got_content = 0, False, False
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = line[len("data: ") :]
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
        pytest.skip(
            f"'{model}' is not a translation model "
            "(set CT2_TEST_MODEL to translategemma-4b-it / nllb-200-distilled-1.3b)"
        )

    label, text, iso, flores = random.choice(_SAMPLES)
    print(f"\n[translate] {label} -> Indonesian  (model={model})")
    print(f"[translate] source: {text}")

    if "nllb" in model:  # FLORES-200 codes
        payload = _infer_payload(
            model,
            messages=[{"role": "user", "content": text}],
            source_lang=flores,
            target_lang="ind_Latn",
        )
    else:  # translategemma, ISO 639-1
        payload = _infer_payload(
            model,
            messages=[{"role": "user", "content": text}],
            source_lang=iso,
            target_lang="id",
        )
    print(
        f"[translate] POST /v1/chat/completions  {json.dumps(payload, ensure_ascii=False)}"
    )

    t0 = time.perf_counter()
    r = _post("/v1/chat/completions", json=payload)
    elapsed = time.perf_counter() - t0
    print(f"[translate] status: {r.status_code}")
    if r.status_code != 200:
        # print the FULL error (pytest's skip reason truncates it)
        print(f"[translate] error body: {r.text}")
        pytest.skip(f"model '{model}' not converted/loadable (see body above)")

    body = r.json()
    translation = body["choices"][0]["message"]["content"]
    usage = body["usage"]
    tps = usage["completion_tokens"] / elapsed if elapsed > 0 else 0.0
    print(f"[translate] indonesian: {translation}")
    print(f"[translate] usage: {usage}")
    print(
        f"[translate] throughput: {usage['completion_tokens']} tokens in "
        f"{elapsed:.2f}s = {tps:.1f} tok/s"
    )
    print(f"[translate] {_resource_line(_get('/admin/status').json())}")

    assert translation.strip(), "empty translation"
    assert body["model"] == model


def test_metrics_score(reachable):
    """Benchmark scoring endpoint: BLEU / ChrF++ over one segment.

    Prints what each metric measures, then the scores. The metric libs are
    optional extras (requirements-metrics.txt); when they're absent the endpoint
    still returns 200 and reports them as unavailable, so this test skips rather
    than fails. Run with `-s` to read the explanations and numbers.
    """
    print("\n[metrics] what the leaderboard measures:")
    for info in _METRIC_INFO.values():
        print(f"[metrics]   - {info}")

    payload = {
        "comet": False,  # keep CI light; COMET is exercised manually on Colab
        "segments": [
            {
                "src": "Le chat dort sur le canapé.",
                "mt": "Kucing tidur di sofa.",
                "ref": "Kucing itu tidur di sofa.",
            }
        ],
    }
    r = _post("/metrics/score", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    print(f"[metrics] available backends: {body['available']}")

    if not body["available"].get("sacrebleu"):
        print(f"[metrics] errors: {body.get('errors')}")
        pytest.skip(
            "sacrebleu not installed server-side "
            "(pip install -r requirements-metrics.txt)"
        )

    system = body["system"]
    print(f"[metrics] system  BLEU={system.get('bleu')}  ChrF++={system.get('chrf')}")
    assert "bleu" in system and "chrf" in system
    assert len(body["segments"]) == 1
    assert 0 <= system["bleu"] <= 100 and 0 <= system["chrf"] <= 100
