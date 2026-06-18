# AI Translate Provider and Model Comparison

A modular, OpenAI-compatible inference server built on **CTranslate2**. It converts
HuggingFace models to the CTranslate2 format, serves them through an
OpenAI-compatible `/v1/chat/completions` API, and lets you **switch models online**
and **track VRAM** through admin endpoints.

Designed to be **written on your laptop, run/prototyped on Google Colab**.

## Why CTranslate2

CTranslate2 is a fast C++/CUDA inference engine that quantizes Transformer
weights (int8/float16) and cuts memory use 2–4x — ideal for fitting 4B models on
a Colab T4. Models must first be **converted** from HuggingFace into CTranslate2's
binary format. See [docs/architecture.md](docs/architecture.md).

Full details and how to add your own models: [docs/models.md](docs/models.md).

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env            # edit as needed

# 1. Convert a model (HF -> CTranslate2)
python -m scripts.convert_model --list
python -m scripts.convert_model qwen3-4b

# 2. Run the API
python run.py                   # or: uvicorn app.server:app --host 0.0.0.0 --port 8000
```

Call it like the OpenAI API:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-4b","messages":[{"role":"user","content":"Hello!"}]}'
```

## Project layout

```
app/
  config.py      # settings + model registry (the only place models are declared)
  converter.py   # HF -> CTranslate2 conversion wrapper
  manager.py     # load/switch/unload, VRAM, prompt building, generate/stream
  schemas.py     # OpenAI-compatible pydantic models
  server.py      # FastAPI app (OpenAI + admin endpoints)
scripts/
  convert_model.py  # CLI converter
  colab_serve.py    # start API + Cloudflare tunnel, print public URL (Colab)
  tunnel.sh         # bare cloudflared quick-tunnel for any port
tests/
  test_api.py       # end-to-end tests against a running server
run.py           # uvicorn entrypoint
requirements.txt / requirements-dev.txt
docs/            # documentation
```

## Expose it from Colab (Cloudflare tunnel)

```python
!python -m scripts.colab_serve     # prints https://<id>.trycloudflare.com/v1
```

Point your laptop / backend at the printed URL as the OpenAI base URL. See
[docs/colab.md](docs/colab.md).

## Tests

```bash
pip install -r requirements-dev.txt
export CT2_TEST_BASE_URL=http://localhost:8000   # or your tunnel URL
pytest tests/ -v
```

The tests hit a live server and skip gracefully if it's unreachable or a model
isn't converted yet. See [docs/testing.md](docs/testing.md).

## Rclone Sync daily driver command

```bash
rclone sync . drive-testbench:autotranslate-ai-provider --progress \
--exclude ".git/**" \
--exclude "app/__pycache__/**" \
--exclude "ct2_models/**" \
--exclude ".pytest_cache/**" \
--exclude "app/__pycache__/**" \
--exclude "scripts/__pycache__/**" \
--exclude "tests/__pycache__/**" \
--dry-run
```

## Docs
- [Architecture](docs/architecture.md)
- [Models & compatibility](docs/models.md)
- [Model behavior](docs/model-behavior.md)
- [API reference](docs/api.md)
- [Running on Google Colab](docs/colab.md)
- [Testing](docs/testing.md)
