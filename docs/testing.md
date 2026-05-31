# Testing

The suite in `tests/test_api.py` is an **end-to-end test against a running
server**. It works the same whether you point it at `localhost` (on Colab) or at
your Cloudflare tunnel URL (from your laptop). It needs no GPU and no ML
libraries — just `pytest` and `requests`.

## Install

```bash
pip install -r requirements-dev.txt
```

## Run

Start the server first (`python run.py`, or `python -m scripts.colab_serve` on
Colab), then:

```bash
export CT2_TEST_BASE_URL=http://localhost:8000   # or https://<id>.trycloudflare.com
pytest tests/ -v
```

Add `-s` to see `print(...)` output (useful for the verbose translation test and
for reading full error bodies that pytest would otherwise truncate):

```bash
pytest tests/ -v -s
```

## Configuration (env vars)

| Var | Default | Purpose |
|---|---|---|
| `CT2_TEST_BASE_URL` | `http://localhost:8000` | server to test (localhost or tunnel URL) |
| `CT2_TEST_API_KEY` | _(none)_ | sent as `Authorization: Bearer ...` if the server enforces a key |
| `CT2_TEST_MODEL` | first `/v1/models` entry | model used for generation tests |
| `CT2_TEST_TIMEOUT` | `120` | per-request timeout (seconds); first call may convert/load a model |

## What it covers

**API surface** (runs without any model converted):
- `GET /v1/models` returns OpenAI-shaped list
- `GET /admin/status` and `GET /admin/vram` respond with expected keys
- unknown model → HTTP `400`
- missing API key → HTTP `401` (only when `CT2_TEST_API_KEY` is set)

**Inference** (auto-skips if the model isn't converted/loadable):
- `POST /v1/chat/completions` returns a `chat.completion` with non-empty content
  and consistent `usage` totals
- streaming (`"stream": true`) yields `text/event-stream` chunks with content
  deltas and terminates with `[DONE]`. Because a stream returns HTTP `200` before
  generation starts, a "model not loadable" error arrives as an in-band
  `data: {"error": ...}` event — the test detects this and skips.

**Translation** (`test_translate_random_to_indonesian`, translation models only):
- picks a random source language (en/fr/es/de/ja) and translates a sample
  sentence **into Indonesian** using `source_lang`/`target_lang`
- skips with `CT2_TEST_MODEL` set to a non-translation model
- it's **verbose**: it prints the source text, request, status, the translation
  and token usage, and the **full error body** on failure (pytest truncates skip
  reasons, so this is the way to see why a model won't load). Use `-s` to view:

```bash
CT2_TEST_MODEL=translategemma-4b-it pytest \
  tests/test_api.py::test_translate_random_to_indonesian -v -s
```

## Graceful skipping

The tests are designed to be safe to run anytime:
- if the **server is unreachable**, the whole suite skips (not fails);
- if **no model is available** yet, only the inference tests skip while the
  surface tests still validate the API.

This means you can run them right after boot to validate wiring, then again after
converting a model to validate generation.

## Testing through the tunnel (from your laptop)

```bash
export CT2_TEST_BASE_URL=https://<id>.trycloudflare.com
export CT2_TEST_MODEL=qwen3-4b
pytest tests/ -v
```

Useful as a quick reverse-proxy health check before pointing your real backend
at the URL.
