"""HuggingFace -> CTranslate2 conversion.

Wraps the `ct2-transformers-converter` command. We shell out to it rather than
calling the Python API because the CLI is the documented, stable interface and
handles every supported architecture uniformly.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .config import ModelSpec, Settings, settings


def is_converted(key: str, cfg: Settings = settings) -> bool:
    """A converted model exists if its dir holds CT2's model.bin."""
    return (cfg.ct2_path(key) / "model.bin").exists()


def convert(
    key: str,
    cfg: Settings = settings,
    quantization: str | None = None,
    force: bool = False,
) -> Path:
    """Convert a registered model to CTranslate2 format.

    Returns the output directory. Idempotent unless force=True.
    """
    spec = cfg.spec(key)
    if spec is None:
        raise KeyError(f"Unknown model key '{key}'. Known: {list(cfg.registry)}")
    if not spec.supported:
        raise ValueError(
            f"Model '{key}' is not supported by CTranslate2. {spec.note}"
        )

    out_dir = cfg.ct2_path(key)
    if is_converted(key, cfg) and not force:
        return out_dir

    quant = quantization or cfg.compute_type
    # CT2 stores weights in fp16/int8; loader applies runtime compute_type.
    store_quant = "int8" if quant.startswith("int8") else "float16"

    cmd = [
        "ct2-transformers-converter",
        "--model", spec.hf_id,
        "--output_dir", str(out_dir),
        "--quantization", store_quant,
        *(["--force"] if force else []),
        *spec.extra_convert_args,
    ]
    # The tokenizer is loaded at runtime from spec.hf_id (HF cache), so we don't
    # copy tokenizer files here -- avoids failures on architectures that ship
    # different tokenizer file layouts.

    env_note = "" if not cfg.hf_token else " (HF_TOKEN set)"
    print(f"[convert] {spec.hf_id} -> {out_dir} quant={store_quant}{env_note}")
    subprocess.run(cmd, check=True)
    return out_dir
