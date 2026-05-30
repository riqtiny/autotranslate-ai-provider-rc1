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
  deltas and terminates with `[DONE]`

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
