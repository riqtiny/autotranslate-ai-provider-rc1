# Architecture

## Overview

```
                 ┌─────────────────────────────────────────────┐
   HF Hub  ──────▶  converter.py  ── ct2-transformers-converter ─┐
                 └─────────────────────────────────────────────┘ │
                                                                  ▼
                                                        ct2_models/<key>/
                                                         (model.bin + vocab)
                                                                  │
 OpenAI client ──HTTP──▶ server.py ──▶ manager.py ──▶ ctranslate2.Generator   (task=generate)
                          (FastAPI)     (lifecycle,    └▶ ctranslate2.Translator  (task=translate)
                                         VRAM, prompts)     (+ HF tokenizer)
```

## Modules

### `config.py` — registry + settings
The single source of truth. A `ModelSpec` declares a model's registry `key`, its
HuggingFace `hf_id`, a `family` (drives prompt format + EOS tokens), and a
`supported` flag with a human-readable `note`. Everything else reads from here, so
adding a model is a one-line registry change (or a `CT2_EXTRA_MODELS` env entry).

Settings are environment-driven (see `.env.example`): device, compute type,
default model, autoswitch, API key, HF token.

### `converter.py` — HF → CTranslate2
Shells out to the documented `ct2-transformers-converter` CLI (the stable,
architecture-agnostic interface). It stores weights as `int8` or `float16` and is
idempotent — it skips models already converted unless `force=True`. The tokenizer
is **not** copied; it's loaded at runtime from the HF id to avoid per-architecture
file-layout issues.

### `manager.py` — runtime
Holds **at most one model in memory** (Colab-friendly). Responsibilities:
- **Lifecycle:** `load` / `switch` / `unload`. Switching unloads the current model,
  runs GC, and calls `torch.cuda.empty_cache()` to actually free VRAM.
- **Auto-convert:** loading an unconverted-but-supported model converts it first.
- **VRAM:** `vram_stats()` reports total/used/free MiB via `torch.cuda.mem_get_info`
  (empty when running on CPU). `ram_stats()` reports system RAM + this process's
  RSS from `/proc` (no extra deps), so CPU-only runs still have memory visibility.
- **Prompts:** renders each model's HF chat template to a string
  (`apply_chat_template(tokenize=False)`) then encodes it, so prompt formatting
  always matches the model and stays robust across transformers versions (some
  return a dict from `tokenize=True`).
- **Inference:** `generate()` (batch) and `stream()` (token-by-token via
  `generate_tokens`, decoded incrementally into text deltas).

### `schemas.py` — OpenAI wire format
Pydantic models for `/v1/chat/completions` (request, response, streaming chunks)
and `/v1/models`. Extra request fields are ignored so real OpenAI clients work
unchanged. `frequency_penalty` is mapped onto CTranslate2's `repetition_penalty`.

### `server.py` — FastAPI
OpenAI-compatible endpoints plus an `/admin` surface for online model switching,
VRAM inspection, and on-demand conversion. On startup it loads the default model
(non-fatal if unavailable); on shutdown it unloads.

## Design choices

- **One model at a time.** Colab GPUs (T4/L4) rarely fit several 4B models. The
  online switcher trades a few seconds of load time for a much smaller footprint.
- **Registry-driven modularity.** No model names are hardcoded in logic; the
  registry is the only coupling point.
- **CLI converter shell-out.** Mirrors the official docs exactly, so new CT2
  releases that add architectures work with no code change.
- **Runtime tokenizer.** Keeps conversion robust and prompt formatting authoritative.

## Request flow (non-streaming)

1. Client POSTs to `/v1/chat/completions` with `model` + `messages`.
2. `manager._require(model)` ensures that model is loaded (auto-switch if enabled).
3. **Decoder-only (`task=generate`):** messages → tokens via the HF chat template,
   then `ctranslate2.Generator.generate_batch(...)` decodes with sampling params.
   **Encoder-decoder (`task=translate`):** the last user message is tokenized as
   source and `ctranslate2.Translator.translate_batch(...)` runs (NLLB forces the
   target language via `target_prefix`).
4. Output token ids are decoded and returned as an OpenAI `chat.completion`.

Streaming uses `generate_tokens` for decoder-only models (`text/event-stream`
`data:` chunks ending with `[DONE]`); translation models emit the full result as
a single chunk.
