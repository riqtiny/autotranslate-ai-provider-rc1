# Running on Google Colab

Workflow: **write code on your laptop → push to GitHub → pull + run on Colab.**
Colab provides the GPU (T4/L4) for conversion and inference.

## 1. Set the runtime

`Runtime → Change runtime type → T4 GPU` (or L4/A100 if available).

## 2. Get the code onto Colab

```python
# Option A: clone your repo
!git clone https://github.com/<you>/autotranslate-ai-provider.git
%cd autotranslate-ai-provider

# Option B: mount Google Drive and work from there (persists across sessions)
from google.colab import drive
drive.mount('/content/drive')
%cd /content/drive/MyDrive/autotranslate-ai-provider
```

## 3. Install dependencies

```python
!pip install -q -r requirements.txt
```

## 4. Configure

```python
import os
os.environ["CT2_DEVICE"] = "cuda"
os.environ["CT2_COMPUTE_TYPE"] = "int8_float16"   # fits a T4
os.environ["CT2_DEFAULT_MODEL"] = "qwen3-4b"
os.environ["CT2_AUTOSWITCH"] = "true"
# For gated models (Gemma family):
os.environ["HF_TOKEN"] = "hf_..."                 # or: !huggingface-cli login
```

> Put converted models on Drive (`CT2_MODELS_DIR=/content/drive/MyDrive/ct2_models`)
> so you don't re-convert every session.

## 5. Convert a model

```python
!python -m scripts.convert_model --list
!python -m scripts.convert_model qwen3-4b
```

Conversion downloads the HF model (several GB) and writes the CTranslate2 binary
to `CT2_MODELS_DIR/<key>`. Do this once per model.

## 6. Run the server + expose it

Colab can't open a public port directly, so tunnel it (Cloudflare Quick Tunnel —
no account or domain needed). The repo ships a helper that starts the API,
downloads `cloudflared`, opens the tunnel, and prints the public URL:

```python
!python -m scripts.colab_serve
```

It prints a banner like:

```
================================================================
  PUBLIC API:  https://random-words.trycloudflare.com/v1
  health:      https://random-words.trycloudflare.com/admin/status
================================================================
```

Point your laptop / existing backend at that `https://...` URL as if it were the
OpenAI API base (`<url>/v1`). The quick-tunnel URL changes each run.

> `scripts/colab_serve.py` runs in the foreground (so the cell keeps streaming
> logs). To run it in the background and keep using the notebook, launch it with
> `subprocess.Popen(["python", "-m", "scripts.colab_serve"])` instead.

### Alternative — bare cloudflared / tunnel.sh

If you'd rather drive it yourself, there's also `scripts/tunnel.sh` (downloads
`cloudflared` and tunnels a port). Run the server and tunnel separately:

```python
import subprocess
subprocess.Popen(["python", "run.py"])           # API on :8000
!bash scripts/tunnel.sh 8000                      # prints https://*.trycloudflare.com
```

### Alternative — ngrok (needs a free authtoken)

```python
!pip install -q pyngrok
from pyngrok import ngrok
ngrok.set_auth_token("YOUR_NGROK_TOKEN")

import subprocess
subprocess.Popen(["python", "run.py"])
print("Public URL:", ngrok.connect(8000))
```

## 7. Smoke test from inside Colab

```python
import requests, time
time.sleep(5)  # give the server a moment to load the default model

print(requests.get("http://localhost:8000/admin/status").json())

r = requests.post("http://localhost:8000/v1/chat/completions", json={
    "model": "qwen3-4b",
    "messages": [{"role": "user", "content": "Give me a haiku about GPUs."}],
})
print(r.json()["choices"][0]["message"]["content"])
```

## 8. Switch models online (watch VRAM)

```python
import requests
print(requests.get("http://localhost:8000/admin/vram").json())
requests.post("http://localhost:8000/admin/switch/translategemma-4b-it")
print(requests.get("http://localhost:8000/admin/vram").json())
```

## 9. Run the translation comparison lab

Open the local Colab URL or the tunnel URL in a browser:

```text
http://localhost:8000/translation-lab
https://<id>.trycloudflare.com/translation-lab
```

The lab lists supported models, switches models online, translates ten popular
source languages into Indonesian, and shows RAM/VRAM after the session. If
`CT2_API_KEY` is set, paste that key into the page before running.

It also **scores and ranks** each model with BLEU/SacreBLEU, ChrF++ and (optional)
COMET in a leaderboard. The metric libraries are optional extras — install them
once:

```python
!pip install -q -r requirements-metrics.txt    # sacrebleu + unbabel-comet
```

- **BLEU + ChrF++** (`sacrebleu`) are pure-Python and always on once installed.
- **COMET** (`unbabel-comet`) is a neural metric — tick the **Score COMET** toggle
  in the page. On first use it downloads a checkpoint (default
  `Unbabel/wmt22-comet-da`, ~2.3 GB). That model is **gated** on HuggingFace, so
  set `HF_TOKEN` (you already need it for the Gemma family) before scoring.
- COMET runs on **CPU by default** (`CT2_COMET_DEVICE=cpu`) so it never competes
  for VRAM with the loaded 4B translation model. For a faster pass set
  `os.environ["CT2_COMET_DEVICE"] = "cuda"` — but ensure there's spare VRAM
  (unload the translation model first, or use a smaller compute type).
- Override the checkpoint with `CT2_COMET_MODEL` if you prefer another COMET model.

Without the extras installed the lab still runs and shows latency/tokens/RAM/VRAM;
the leaderboard simply notes that the metrics are unavailable.

## 10. Run the test suite

The API tests in `tests/` hit a live server, so point them at localhost (in
Colab) or your tunnel URL (from your laptop):

```python
!pip install -q -r requirements-dev.txt
!CT2_TEST_BASE_URL=http://localhost:8000 CT2_TEST_MODEL=qwen3-4b pytest tests/ -v

# Verbose translation test (random language -> Indonesian); -s shows the output
!CT2_TEST_BASE_URL=http://localhost:8000 CT2_TEST_MODEL=translategemma-4b-it \
    pytest tests/test_api.py::test_translate_random_to_indonesian -v -s
```

See [testing.md](testing.md) for full details.

## Tips for the T4 (16 GB)

- Use `int8_float16`. A 4B model lands around 4–5 GB this way.
- Only one model is held in memory; switching frees the previous one.
- Keep `CT2_MODELS_DIR` on Drive to skip re-conversion.
- First request after a switch is slower (model load + tokenizer fetch).
- If you hit OOM, lower `max_tokens` or restart the runtime to clear fragmentation.
```
