# API reference

Base URL: `http://<host>:<port>` (default `http://localhost:8000`).

If `CT2_API_KEY` is set, send `Authorization: Bearer <key>` on every request.

## OpenAI-compatible endpoints

### `GET /v1/models`
Lists supported (convertible) models in OpenAI format.

```json
{ "object": "list", "data": [ { "id": "qwen3-4b", "object": "model", "owned_by": "ctranslate2" } ] }
```

### `POST /v1/chat/completions`

Request fields (OpenAI-compatible; unknown fields ignored):

| Field | Default | Notes |
|---|---|---|
| `model` | — | registry key, e.g. `qwen3-4b` |
| `messages` | — | `[{ "role": "...", "content": "..." }]` |
| `max_tokens` | 512 | max generated tokens |
| `temperature` | 0.7 | |
| `top_p` | 1.0 | |
| `top_k` | 0 | extra (0 = disabled) |
| `frequency_penalty` | 0.0 | mapped → CT2 `repetition_penalty` |
| `stream` | false | SSE streaming when true |

**Non-streaming:**

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-4b","messages":[{"role":"user","content":"Say hi in 3 words."}]}'
```

```json
{
  "id": "chatcmpl-...", "object": "chat.completion", "model": "qwen3-4b",
  "choices": [{ "index": 0, "message": {"role":"assistant","content":"Hi there friend"}, "finish_reason": "stop" }],
  "usage": { "prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15 }
}
```

**Streaming** (`"stream": true`) emits `text/event-stream`:

```
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"}}]}
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hi"}}]}
...
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{},"finish_reason":"stop"}]}
data: [DONE]
```

### Using the official OpenAI client

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed-or-your-key")

resp = client.chat.completions.create(
    model="qwen3-4b",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp.choices[0].message.content)
```

### Calling TranslateGemma

TranslateGemma expects source/target language codes. With this server you embed
the instruction in the message content (the HF chat template handles formatting):

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"translategemma-4b-it","messages":[{"role":"user","content":"Translate from en to fr: The house is wonderful."}]}'
```

> TranslateGemma's native template uses structured `source_lang_code` /
> `target_lang_code` fields and is translation-only. This server exposes the
> general chat surface; for strict native formatting, convert and call the model
> directly (see [models.md](models.md)).

## Admin endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/status` | loaded model, device, compute type, VRAM, full registry state |
| `GET` | `/admin/vram` | GPU memory snapshot (MiB) |
| `POST` | `/admin/switch/{key}` | **online model switch** (loads, auto-converts if needed) |
| `POST` | `/admin/unload` | free the GPU |
| `POST` | `/admin/convert/{key}?force=true` | convert a model on demand |

```bash
# See what's loaded and how much VRAM is in use
curl http://localhost:8000/admin/status

# Switch models without restarting the server
curl -X POST http://localhost:8000/admin/switch/gemma3-4b-it

# VRAM only
curl http://localhost:8000/admin/vram
```

`/admin/vram` example:

```json
{ "device": "Tesla T4", "total_mib": 15360, "used_mib": 4210, "free_mib": 11150, "reserved_by_torch_mib": 0 }
```

## Errors

Bad model keys, unsupported models, or unconverted models return HTTP `400` with
`{"detail": "..."}`. A missing/invalid API key (when configured) returns `401`.

## Reverse-proxying from Colab to your laptop

When the server runs on Colab, expose it with a Cloudflare Quick Tunnel:

```python
!python -m scripts.colab_serve     # prints https://<id>.trycloudflare.com/v1
```

Then use the printed URL as your OpenAI base URL from anywhere:

```python
from openai import OpenAI
client = OpenAI(base_url="https://<id>.trycloudflare.com/v1", api_key="your-key-or-anything")
```

Notes:
- The quick-tunnel URL is regenerated each run; re-read it after restarting.
- If you set `CT2_API_KEY`, the tunnel is public — clients must send the Bearer
  key. Setting a key is strongly recommended once the endpoint is reachable from
  the internet.
- See [colab.md](colab.md) for the full Colab + tunnel walkthrough and
  [testing.md](testing.md) to health-check the tunnel.
