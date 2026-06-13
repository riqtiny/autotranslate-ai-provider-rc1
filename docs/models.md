# Models & compatibility

> For how each model behaves at request time (prompting, thinking mode, stop
> tokens, translation inputs), see [model-behavior.md](model-behavior.md).

## Your requested models vs. CTranslate2 support

CTranslate2 only supports a curated set of architectures. As of CTranslate2 4.7
(verified against the official Transformers guide), here is where the three
requested models stand:

### 1. `Qwen/Qwen3.5-4B` — ❌ not supported
CTranslate2 supports **Qwen 2.5** and **Qwen 3**, not Qwen 3.5. Qwen3.5-4B is also
a multimodal (image-text-to-text) model, which CTranslate2 does not handle.

**Substitute shipped:** registry key `qwen3-4b` → `Qwen/Qwen3-4B` (text-only,
officially supported and documented by CTranslate2). MoE Qwen variants are not
supported.

### 2. `google/gemma-4-E4B-it` — ❌ not supported
The CTranslate2 docs are explicit: for Gemma 4, *"Only the 31B dense model is
supported. The MoE variants (E2B, E4B) are not supported."* The 31B dense model
won't fit a Colab T4 anyway.

**Substitute shipped:** registry key `gemma3-4b-it` → `google/gemma-3-4b-it`
(Gemma 3, text-only path, supported by CTranslate2 and Colab-sized).

> Note: the requested id looks like a mix of `gemma-4` and the Gemma 3n `E4B`
> naming. Neither the Gemma 3n `E4B` nor Gemma 4 `E4B` MoE models are convertible.

### 3. `google/translategemma-4b-it` — ⚠️ works text-only
TranslateGemma is **Gemma-3-based** and multimodal (it can translate text in
images). CTranslate2 supports "Gemma 3 (text only)", so the text translation path
can be converted. Image input is dropped. Its chat template is translation-only
and **requires language codes**: call it with `source_lang` and `target_lang`
fields (the server maps them into the model's structured `source_lang_code` /
`target_lang_code` template). See [api.md](api.md#calling-translation-models).

**Shipped as:** registry key `translategemma-4b-it`.

### 4. `facebook/nllb-200-distilled-1.3B` — ✅ encoder-decoder
NLLB-200 is Meta's multilingual translation model covering **200 languages**.
This is the **distilled 1.3B** variant — smaller and faster, a good fit for a
Colab T4.
It's an **encoder-decoder** model, so the server runs it through
`ctranslate2.Translator` (not `Generator`). It uses **FLORES-200 language codes**
(e.g. `eng_Latn`, `ind_Latn`, `fra_Latn`) — pass them as `source_lang` /
`target_lang`. The full list is in the
[FLORES-200 README](https://github.com/facebookresearch/flores/blob/main/flores200/README.md#languages-in-flores-200).

**Shipped as:** registry key `nllb-200-distilled-1.3b` (`task=translate`).

### 5. `google/t5gemma-2-4b-4b` — ✅ encoder-decoder
T5Gemma is Google's encoder-decoder (text-to-text) family, built by adapting
decoder-only Gemma into a seq2seq model. CTranslate2 supports T5Gemma, so it runs
through `ctranslate2.Translator`. It's **general text-to-text** — instruct it via
the prompt (e.g. `"Translate to Indonesian: ..."`); it does **not** need
`source_lang`/`target_lang`.

**Shipped as:** registry key `t5gemma-2-4b-4b` (`task=translate`).

## The registry

All models live in `app/config.py` as `ModelSpec` entries:

| Key | HF id | Family | Task | Supported |
|---|---|---|---|---|
| `qwen3-4b` | `Qwen/Qwen3-4B` | qwen | generate | ✅ |
| `gemma3-4b-it` | `google/gemma-3-4b-it` | gemma | generate | ✅ |
| `translategemma-4b-it` | `google/translategemma-4b-it` | translategemma | generate | ✅ (text-only) |
| `nllb-200-distilled-1.3b` | `facebook/nllb-200-distilled-1.3B` | nllb | translate | ✅ (enc-dec) |
| `t5gemma-2-4b-4b` | `google/t5gemma-2-4b-4b` | t5gemma | translate | ✅ (enc-dec) |

The `task` field selects the CTranslate2 engine: `generate` → `Generator`
(decoder-only models), `translate` → `Translator` (encoder-decoder / seq2seq).

Unsupported entries are intentionally kept so the API can explain *why* and so
they're trivial to enable if CTranslate2 adds support later.

## Adding your own model

CTranslate2-supported families include: Llama, Qwen 2.5/3, Gemma 2/3, Falcon, MPT,
GPT-2/J/NeoX, BLOOM, OPT, T5, NLLB, M2M100, Whisper, and more.

**Option A — edit the registry** (`app/config.py`), add to `_DEFAULT_MODELS`:

```python
ModelSpec(key="llama3-8b", hf_id="meta-llama/Meta-Llama-3-8B-Instruct", family="llama"),
```

**Option B — no code change**, set an env var (JSON list):

```bash
export CT2_EXTRA_MODELS='[{"key":"llama3-8b","hf_id":"meta-llama/Meta-Llama-3-8B-Instruct","family":"llama"}]'
```

Then convert and use:

```bash
python -m scripts.convert_model llama3-8b
curl ... -d '{"model":"llama3-8b", ...}'
```

The `family` field controls EOS tokens (`qwen` → `<|im_end|>`, `gemma`/
`translategemma` → `<end_of_turn>`); any other value falls back to the
tokenizer's own EOS. Prompt formatting always uses the model's HF chat template.

For the `qwen` family, Qwen3's default "thinking mode" is disabled
(`enable_thinking=False`) so the model answers directly instead of emitting
`<think>...</think>` reasoning — better suited to translation/chat use.

## Gated models (Gemma, Llama)

Gemma and Llama require accepting a license on HuggingFace. Set `HF_TOKEN` in
`.env` (or run `huggingface-cli login`) before converting.

## Quantization

Set `CT2_COMPUTE_TYPE` (default `int8_float16`):

| Value | VRAM | Quality | Notes |
|---|---|---|---|
| `int8_float16` | lowest | very good | recommended for T4 |
| `float16` | medium | best | needs more VRAM |
| `int8` | low | good | CPU-friendly |
| `float32` | highest | reference | CPU / debugging |
