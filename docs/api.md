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
| `source_lang` | — | extra; **required** by translation models (e.g. `en`) |
| `target_lang` | — | extra; **required** by translation models (e.g. `fr`) |

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

**Streaming errors are in-band.** For a streamed request the HTTP status is `200`
and headers are sent *before* generation starts, so an error that occurs while
streaming (e.g. the model isn't converted/loadable) can't change the status code.
Instead it's emitted as a `data:` event and the stream then closes:

```
data: {"error":{"message":"Model 'qwen3-4b' is not converted yet. ...","type":"invalid_request_error"}}
```

Non-streaming requests return these same errors as an HTTP `400` (see [Errors](#errors)).
Clients consuming the raw stream should check each event for an `"error"` key.

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

### Calling translation models

The server ships three translation models, each with slightly different inputs.
In all cases the text to translate is the **last user message**.

**TranslateGemma** (`translategemma-4b-it`) — requires ISO 639-1 codes (`en`,
`fr`, `de`) or regionalized (`en-US`, `de-DE`) as `source_lang`/`target_lang`:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "translategemma-4b-it",
        "messages": [{"role": "user", "content": "The house is wonderful."}],
        "source_lang": "en",
        "target_lang": "fr"
      }'
```

**NLLB-200** (`nllb-200-distilled-1.3b`, encoder-decoder) — requires **FLORES-200** codes
(`eng_Latn`, `ind_Latn`, `zho_Hans`, …) as `source_lang`/`target_lang`:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "nllb-200-distilled-1.3b",
        "messages": [{"role": "user", "content": "The house is wonderful."}],
        "source_lang": "eng_Latn",
        "target_lang": "ind_Latn"
      }'
```

**T5Gemma** (`t5gemma-2-4b-4b`, encoder-decoder) — general text-to-text, **no
language codes**; instruct it in the prompt:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "t5gemma-2-4b-4b",
        "messages": [{"role": "user", "content": "Translate to Indonesian: The house is wonderful."}]
      }'
```

If `source_lang`/`target_lang` are missing for a model that needs them
(TranslateGemma, NLLB), the request returns HTTP `400`. These fields are ignored
by chat models (`qwen3-4b`, `gemma3-4b-it`) and by T5Gemma. For full per-model
behavior see [model-behavior.md](model-behavior.md).

## Admin endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/status` | loaded model, device, compute type, VRAM, RAM, full registry state |
| `GET` | `/admin/vram` | GPU memory snapshot (MiB); `{}` when no CUDA |
| `GET` | `/admin/ram` | system RAM + process RSS snapshot (MiB) |
| `POST` | `/admin/switch/{key}` | **online model switch** (loads, auto-converts if needed) |
| `POST` | `/admin/unload` | free the GPU |
| `POST` | `/admin/convert/{key}?force=true` | convert a model on demand |

```bash
# See what's loaded and how much VRAM/RAM is in use
curl http://localhost:8000/admin/status

# Switch models without restarting the server
curl -X POST http://localhost:8000/admin/switch/gemma3-4b-it

# VRAM only / RAM only
curl http://localhost:8000/admin/vram
curl http://localhost:8000/admin/ram
```

`/admin/vram` example (empty `{}` when running on CPU):

```json
{ "device": "Tesla T4", "total_mib": 15360, "used_mib": 4210, "free_mib": 11150, "reserved_by_torch_mib": 0 }
```

`/admin/ram` example (useful when `device` is `cpu` and there's no VRAM):

```json
{ "total_mib": 12979, "used_mib": 3859, "available_mib": 9120, "process_rss_mib": 4530 }
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
