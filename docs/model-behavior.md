# Model behavior

How each registered model behaves at request time — prompting, special modes,
stop tokens, and quirks. Behavior is selected by the model's `family` field in
the registry (`app/config.py`); everything else is shared.

Summary:

| Key | Family | Type | Prompt input | Special behavior | Stop tokens |
|---|---|---|---|---|---|
| `qwen3-4b` | `qwen` | chat / general | `messages` | thinking mode **off** | `<|im_end|>`, eos |
| `gemma3-4b-it` | `gemma` | chat / general | `messages` | text-only (no images) | `<end_of_turn>`, eos |
| `translategemma-4b-it` | `translategemma` | translation only | `messages` + `source_lang`/`target_lang` | structured translate template | `<end_of_turn>`, eos |
| `nllb-200-distilled-1.3b` | `nllb` | translation (enc-dec) | `messages` + FLORES `source_lang`/`target_lang` | `Translator`, target-prefix forcing | model eos |
| `t5gemma-2-4b-4b` | `t5gemma` | translation (enc-dec) | `messages` (instruct via prompt) | `Translator`, text-to-text | model eos |

Two engine types (set by the registry `task` field):
- **`generate` (decoder-only):** `qwen`, `gemma`, `translategemma`. Prompts are
  rendered with the model's HF chat template; supports streaming token-by-token.
- **`translate` (encoder-decoder):** `nllb`, `t5gemma`. Run via
  `ctranslate2.Translator`; the last user message is the source text. Streaming
  returns the full translation as a single chunk.

Shared behavior (all families):
- Sampling params map from the OpenAI request: `temperature`, `top_p`, `top_k`,
  and `frequency_penalty` → CTranslate2 `repetition_penalty`.
- `temperature: 0` is sent as a tiny value (`1e-4`) ≈ greedy decoding.
- Generation stops on the family stop tokens above or at `max_tokens`.

---

## `qwen3-4b` — Qwen3 4B (general chat)

- **Use for:** general chat, instruction following, and translation-by-prompt.
- **Input:** standard OpenAI `messages` (system/user/assistant).
- **Thinking mode is disabled.** Qwen3 ships with a "thinking mode" that emits
  `<think>...</think>` reasoning before the answer. This server passes
  `enable_thinking=False` to the template so it answers directly — better for
  translation/chat and lower latency. (To re-enable, remove that flag in
  `manager.build_tokens`.)
- **Translation:** not purpose-built; instruct it, e.g.
  `"Translate to Indonesian: <text>"`. Quality is decent but below TranslateGemma.
- **Stops on:** `<|im_end|>` and the tokenizer EOS.

```bash
curl localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"qwen3-4b",
  "messages":[{"role":"user","content":"Translate to Indonesian: Good morning."}]
}'
```

## `gemma3-4b-it` — Gemma 3 4B instruction-tuned (general chat)

- **Use for:** general chat / instruction following.
- **Input:** standard OpenAI `messages`.
- **Text-only.** Gemma 3 is multimodal upstream, but CTranslate2 converts the
  **text path only** — image inputs are not supported here.
- **No thinking mode** — answers directly.
- **Stops on:** `<end_of_turn>` (set as the default EOS for instruction-tuned
  Gemma during conversion) and the tokenizer EOS.

```bash
curl localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"gemma3-4b-it",
  "messages":[{"role":"user","content":"Explain CTranslate2 in one sentence."}]
}'
```

## `translategemma-4b-it` — TranslateGemma 4B (translation only)

- **Use for:** translation across 55 languages. This is the recommended model
  when translation quality matters.
- **Input:** `messages` **plus** `source_lang` and `target_lang`. The text to
  translate is taken from the last user message; the server wraps it into
  TranslateGemma's required structured template
  (`type`/`source_lang_code`/`target_lang_code`/`text`).
- **Language codes:** ISO 639-1 (`en`, `fr`, `id`, `ja`) or regionalized
  (`en-US`, `de-DE`).
- **Strict template.** It is translation-only and rejects plain chat. Omitting
  `source_lang`/`target_lang` returns HTTP `400` with a clear message.
- **Text-only.** The upstream model can translate text inside images; that image
  path is dropped in the CTranslate2 (text-only) conversion.
- **Stops on:** `<end_of_turn>` and the tokenizer EOS.

```bash
curl localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"translategemma-4b-it",
  "messages":[{"role":"user","content":"Le chat dort sur le canapé."}],
  "source_lang":"fr","target_lang":"id"
}'
```

> `source_lang`/`target_lang` are ignored by the chat families (`qwen`,
> `gemma`), so it's harmless to always send them from a generic client.

## `nllb-200-distilled-1.3b` — NLLB-200 distilled 1.3B (encoder-decoder, 200 languages)

- **Engine:** `ctranslate2.Translator` (encoder-decoder), `task=translate`.
- **Use for:** high-coverage translation across 200 languages, including
  low-resource ones.
- **Input:** the last user message is the source text. **Requires FLORES-200
  codes** as `source_lang`/`target_lang` (e.g. `eng_Latn`, `ind_Latn`,
  `zho_Hans`). Missing codes → HTTP `400`.
- **How it works:** the tokenizer's `src_lang` is set, and the target language is
  forced as the decoder `target_prefix`; the forced token is stripped from the
  output.
- **Streaming:** returns the whole translation as one chunk.
- **Stops on:** the model's EOS token.

```bash
curl localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"nllb-200-distilled-1.3b",
  "messages":[{"role":"user","content":"The weather is beautiful today."}],
  "source_lang":"eng_Latn","target_lang":"ind_Latn"
}'
```

## `t5gemma-2-4b-4b` — T5Gemma (encoder-decoder, text-to-text)

- **Engine:** `ctranslate2.Translator` (encoder-decoder), `task=translate`.
- **Use for:** general text-to-text, including translation by instruction.
- **Input:** the last user message is the source text. **No language codes** —
  instruct it in the prompt, e.g. `"Translate to Indonesian: <text>"`.
  `source_lang`/`target_lang` are ignored if sent.
- **Streaming:** returns the whole output as one chunk.
- **Stops on:** the model's EOS token.

```bash
curl localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model":"t5gemma-2-4b-4b",
  "messages":[{"role":"user","content":"Translate to Indonesian: The weather is beautiful today."}]
}'
```

See [models.md](models.md) for the full compatibility rationale and how to add
your own models.
