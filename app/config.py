"""Settings and the model registry.

The registry is the single place that knows about models. Add an entry here
(or via CT2_EXTRA_MODELS json) and the converter, manager and API pick it up
automatically. Nothing else in the codebase hardcodes a model name.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:  # load .env if python-dotenv is present, but don't require it
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_bool(key: str, default: bool) -> bool:
    val = _env(key)
    if not val:
        return default
    return val.lower() in ("1", "true", "yes", "on")


@dataclass
class ModelSpec:
    """Describes one model and how to convert/run it.

    family drives prompt formatting and EOS handling. Supported families:
    "qwen", "gemma", "translategemma". Unknown families fall back to a plain
    chat template via the HF tokenizer.
    """

    key: str  # registry id used by the API ("model" field)
    hf_id: str  # HuggingFace repo to convert from
    family: str  # prompt/eos behavior selector
    task: str = "generate"  # "generate" (decoder) or "translate" (enc-dec)
    supported: bool = True  # known to work with current CTranslate2
    note: str = ""  # human-facing compatibility note
    extra_convert_args: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# --- The registry -----------------------------------------------------------
# Both the user's intended targets and the CTranslate2-supported substitutes
# are listed. Unsupported entries are kept so the API can report *why* and so
# they're trivial to enable if CTranslate2 adds support later.
_DEFAULT_MODELS: list[ModelSpec] = [
    ModelSpec(
        key="qwen3-4b",
        hf_id="Qwen/Qwen3-4B",
        family="qwen",
        note="CTranslate2-supported model Qwen3-4B",
    ),
    ModelSpec(
        key="gemma3-4b-it",
        hf_id="google/gemma-3-4b-it",
        family="gemma",
        note="CTranslate2-supported (text-only) substitute for the requested ",
    ),
    # Requested translation model. Gemma-3 based, multimodal; text-only path may
    # work with CTranslate2's Gemma 3 support. Marked supported but flagged.
    ModelSpec(
        key="translategemma-4b-it",
        hf_id="google/translategemma-4b-it",
        family="translategemma",
        note="Gemma-3-based translation model. Text-only conversion via "
        "CTranslate2's Gemma 3 support; image input is dropped.",
    ),
    # Encoder-decoder (seq2seq) models -> ctranslate2.Translator, not Generator.
    ModelSpec(
        key="nllb-200-distilled-1.3b",
        hf_id="facebook/nllb-200-distilled-1.3B",
        family="nllb",
        task="translate",
        note="Meta NLLB-200 distilled (1.3B), 200 languages. Needs FLORES-200 "
        "codes as source_lang/target_lang (e.g. 'eng_Latn', 'ind_Latn').",
    ),
    ModelSpec(
        key="t5gemma-2-4b-4b",
        hf_id="google/t5gemma-2-4b-4b",
        family="t5gemma",
        task="translate",
        note="Google T5Gemma encoder-decoder (text-to-text). Instruct via the "
        "prompt; source_lang/target_lang not required.",
    ),
]


def _load_extra_models() -> list[ModelSpec]:
    raw = _env("CT2_EXTRA_MODELS")
    if not raw:
        return []
    out = []
    for item in json.loads(raw):
        out.append(ModelSpec(**item))
    return out


@dataclass
class Settings:
    models_dir: Path = field(
        default_factory=lambda: Path(_env("CT2_MODELS_DIR", "./ct2_models"))
    )
    device: str = field(default_factory=lambda: _env("CT2_DEVICE", "cuda"))
    compute_type: str = field(
        default_factory=lambda: _env("CT2_COMPUTE_TYPE", "int8_float16")
    )
    default_model: str = field(
        default_factory=lambda: _env("CT2_DEFAULT_MODEL", "qwen3-4b")
    )
    autoswitch: bool = field(default_factory=lambda: _env_bool("CT2_AUTOSWITCH", True))
    host: str = field(default_factory=lambda: _env("CT2_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(_env("CT2_PORT", "8000")))
    api_key: str = field(default_factory=lambda: _env("CT2_API_KEY"))
    hf_token: str = field(default_factory=lambda: _env("HF_TOKEN"))

    registry: dict[str, ModelSpec] = field(init=False)

    def __post_init__(self) -> None:
        self.models_dir = Path(self.models_dir)
        self.registry = {m.key: m for m in _DEFAULT_MODELS}
        for m in _load_extra_models():
            self.registry[m.key] = m

    def spec(self, key: str) -> ModelSpec | None:
        return self.registry.get(key)

    def ct2_path(self, key: str) -> Path:
        """Local directory where the converted CT2 model lives."""
        return self.models_dir / key


settings = Settings()
