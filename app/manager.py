"""Runtime model manager: load/switch/unload, VRAM, prompt building, inference.

Holds at most one model in memory at a time (Colab-friendly). Switching unloads
the current model first. All model knowledge comes from the registry in config.
"""
from __future__ import annotations

import gc
import threading
import time
from dataclasses import dataclass
from typing import Iterator

from .config import ModelSpec, Settings, settings
from .converter import convert, is_converted


# --- VRAM ---------------------------------------------------------------------
def vram_stats() -> dict:
    """Best-effort GPU memory stats in MiB. Empty dict if no CUDA/torch."""
    try:
        import torch

        if not torch.cuda.is_available():
            return {}
        free, total = torch.cuda.mem_get_info()
        reserved = torch.cuda.memory_reserved()
        mib = 1024 * 1024
        return {
            "device": torch.cuda.get_device_name(0),
            "total_mib": round(total / mib),
            "used_mib": round((total - free) / mib),
            "free_mib": round(free / mib),
            "reserved_by_torch_mib": round(reserved / mib),
        }
    except Exception:
        return {}


@dataclass
class LoadedModel:
    spec: ModelSpec
    generator: object        # ctranslate2.Generator
    tokenizer: object        # transformers tokenizer
    end_tokens: list[str]
    loaded_at: float


class ModelManager:
    def __init__(self, cfg: Settings = settings) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()
        self._current: LoadedModel | None = None

    # --- introspection -------------------------------------------------------
    @property
    def current_key(self) -> str | None:
        return self._current.spec.key if self._current else None

    def status(self) -> dict:
        return {
            "loaded_model": self.current_key,
            "device": self.cfg.device,
            "compute_type": self.cfg.compute_type,
            "vram": vram_stats(),
            "models": [
                {
                    "id": s.key,
                    "hf_id": s.hf_id,
                    "family": s.family,
                    "supported": s.supported,
                    "converted": is_converted(s.key, self.cfg),
                    "loaded": s.key == self.current_key,
                    "note": s.note,
                }
                for s in self.cfg.registry.values()
            ],
        }

    # --- lifecycle -----------------------------------------------------------
    def load(self, key: str, *, auto_convert: bool = True) -> LoadedModel:
        with self._lock:
            if self._current and self._current.spec.key == key:
                return self._current

            spec = self.cfg.spec(key)
            if spec is None:
                raise KeyError(f"Unknown model '{key}'.")
            if not spec.supported:
                raise ValueError(f"Model '{key}' is not supported: {spec.note}")

            if not is_converted(key, self.cfg):
                if not auto_convert:
                    raise FileNotFoundError(
                        f"Model '{key}' is not converted yet. Run conversion first."
                    )
                convert(key, self.cfg)

            self._unload_locked()

            import ctranslate2
            import transformers

            generator = ctranslate2.Generator(
                str(self.cfg.ct2_path(key)),
                device=self.cfg.device,
                compute_type=self.cfg.compute_type,
            )
            tokenizer = transformers.AutoTokenizer.from_pretrained(
                spec.hf_id, token=self.cfg.hf_token or None
            )
            self._current = LoadedModel(
                spec=spec,
                generator=generator,
                tokenizer=tokenizer,
                end_tokens=_end_tokens(spec, tokenizer),
                loaded_at=time.time(),
            )
            return self._current

    def switch(self, key: str) -> LoadedModel:
        return self.load(key)

    def unload(self) -> None:
        with self._lock:
            self._unload_locked()

    def _unload_locked(self) -> None:
        if self._current is not None:
            del self._current.generator
            self._current = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def _require(self, key: str | None) -> LoadedModel:
        """Resolve which model to use, honoring autoswitch."""
        if key and (not self._current or self._current.spec.key != key):
            if self.cfg.autoswitch:
                return self.load(key)
            raise ValueError(
                f"Model '{key}' is not loaded and autoswitch is off."
            )
        if self._current is None:
            if not key:
                raise ValueError("No model loaded and no model specified.")
            return self.load(key)
        return self._current

    # --- prompt building -----------------------------------------------------
    def build_tokens(self, lm: LoadedModel, messages: list[dict], *,
                     source_lang: str | None = None,
                     target_lang: str | None = None) -> list[str]:
        tok = lm.tokenizer
        kwargs = {}
        if lm.spec.family == "translategemma":
            # TranslateGemma's template requires structured content with language
            # codes, not a plain string. Build it from the last user message.
            messages = self._translategemma_messages(messages, source_lang, target_lang)
        elif lm.spec.family == "qwen":
            # Qwen3 enables a "thinking mode" by default; disable it so the model
            # answers directly (e.g. for translation) instead of reasoning.
            kwargs["enable_thinking"] = False
        # Render to a string first (tokenize=False), then encode. Doing this
        # avoids version differences where tokenize=True returns a dict
        # ({"input_ids": ...}) instead of a flat id list.
        try:
            prompt = tok.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False, **kwargs
            )
        except Exception as e:  # surface template errors as clean 400s
            raise ValueError(f"chat template error: {e}")
        ids = tok.encode(prompt, add_special_tokens=False)
        return tok.convert_ids_to_tokens(ids)

    @staticmethod
    def _translategemma_messages(messages, source_lang, target_lang):
        if not source_lang or not target_lang:
            raise ValueError(
                "translategemma requires 'source_lang' and 'target_lang' "
                "(e.g. 'en', 'fr', 'de-DE') in the request."
            )
        text = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), None
        )
        if not text:
            raise ValueError("no user message to translate.")
        return [{
            "role": "user",
            "content": [{
                "type": "text",
                "source_lang_code": source_lang,
                "target_lang_code": target_lang,
                "text": text,
            }],
        }]

    # --- inference -----------------------------------------------------------
    def generate(self, messages: list[dict], *, model: str | None = None,
                 max_tokens: int = 512, temperature: float = 0.7,
                 top_p: float = 1.0, top_k: int = 0,
                 repetition_penalty: float = 1.0,
                 source_lang: str | None = None,
                 target_lang: str | None = None) -> dict:
        lm = self._require(model)
        tokens = self.build_tokens(lm, messages, source_lang=source_lang,
                                   target_lang=target_lang)
        results = lm.generator.generate_batch(
            [tokens],
            max_length=max_tokens,
            sampling_temperature=max(temperature, 1e-4),
            sampling_topp=top_p,
            sampling_topk=top_k,
            repetition_penalty=repetition_penalty,
            include_prompt_in_result=False,
            end_token=lm.end_tokens,
        )
        out_ids = results[0].sequences_ids[0]
        text = lm.tokenizer.decode(out_ids, skip_special_tokens=True)
        return {
            "text": text,
            "model": lm.spec.key,
            "prompt_tokens": len(tokens),
            "completion_tokens": len(out_ids),
        }

    def stream(self, messages: list[dict], *, model: str | None = None,
               max_tokens: int = 512, temperature: float = 0.7,
               top_p: float = 1.0, top_k: int = 0,
               repetition_penalty: float = 1.0,
               source_lang: str | None = None,
               target_lang: str | None = None) -> Iterator[str]:
        lm = self._require(model)
        tokens = self.build_tokens(lm, messages, source_lang=source_lang,
                                   target_lang=target_lang)
        step_results = lm.generator.generate_tokens(
            tokens,
            max_length=max_tokens,
            sampling_temperature=max(temperature, 1e-4),
            sampling_topp=top_p,
            sampling_topk=top_k,
            repetition_penalty=repetition_penalty,
            end_token=lm.end_tokens,
        )
        acc: list[int] = []
        prev = ""
        for step in step_results:
            acc.append(step.token_id)
            text = lm.tokenizer.decode(acc, skip_special_tokens=True)
            if len(text) > len(prev):
                yield text[len(prev):]
                prev = text


def _end_tokens(spec: ModelSpec, tokenizer) -> list[str]:
    """EOS tokens that should stop generation, per family."""
    ends: list[str] = []
    if spec.family in ("gemma", "translategemma"):
        ends.append("<end_of_turn>")
    if spec.family == "qwen":
        ends.append("<|im_end|>")
    if tokenizer.eos_token and tokenizer.eos_token not in ends:
        ends.append(tokenizer.eos_token)
    return ends


manager = ModelManager()
