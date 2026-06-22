"""Translation-quality metrics: BLEU/SacreBLEU, ChrF++, and COMET.

Self-contained and dependency-soft. The metric libraries (`sacrebleu`,
`unbabel-comet`) are optional extras (see requirements-metrics.txt) — nothing
here is imported at module load, so the server still boots without them. Each
scorer degrades gracefully: lexical metrics (BLEU/ChrF++) work the moment
`sacrebleu` is installed; COMET is a heavy neural metric loaded lazily and
cached as a singleton, and reports as unavailable until `unbabel-comet` is
present.

ChrF++ is SacreBLEU's chrF with word bigrams (`word_order=2`), `char_order=6`,
`beta=2` — the canonical "++" configuration.
"""

from __future__ import annotations

import os
import threading

# chrF++ knobs (SacreBLEU canonical settings).
_CHRF_CHAR_ORDER = 6
_CHRF_WORD_ORDER = 2  # the "++": adds word bigrams on top of character n-grams
_CHRF_BETA = 2

_COMET_MODEL_ID = os.environ.get("CT2_COMET_MODEL", "Unbabel/wmt22-comet-da").strip()
# Default to CPU so COMET never contends for VRAM with the loaded translation
# model on a Colab T4. Set CT2_COMET_DEVICE=cuda for a faster GPU pass.
_COMET_DEVICE = os.environ.get("CT2_COMET_DEVICE", "cpu").strip().lower()

_comet_lock = threading.Lock()
_comet_model = None  # cached singleton once loaded


def _has(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


def available() -> dict:
    """Which metric backends are importable right now."""
    return {"sacrebleu": _has("sacrebleu"), "comet": _has("comet")}


def lexical_scores(hyps: list[str], refs: list[str]) -> dict:
    """Per-segment and corpus BLEU + ChrF++ via sacrebleu.

    Returns {"segments": [{"bleu": float, "chrf": float}, ...],
             "system": {"bleu": float, "chrf": float}}.
    """
    import sacrebleu

    segments = []
    for hyp, ref in zip(hyps, refs):
        sb = sacrebleu.sentence_bleu(hyp, [ref])
        sc = sacrebleu.sentence_chrf(
            hyp,
            [ref],
            char_order=_CHRF_CHAR_ORDER,
            word_order=_CHRF_WORD_ORDER,
            beta=_CHRF_BETA,
        )
        segments.append({"bleu": round(sb.score, 2), "chrf": round(sc.score, 2)})

    # corpus_* expects a list of reference streams: [[ref0, ref1, ...]].
    corpus_bleu = sacrebleu.corpus_bleu(hyps, [refs])
    corpus_chrf = sacrebleu.corpus_chrf(
        hyps,
        [refs],
        char_order=_CHRF_CHAR_ORDER,
        word_order=_CHRF_WORD_ORDER,
        beta=_CHRF_BETA,
    )
    system = {
        "bleu": round(corpus_bleu.score, 2),
        "chrf": round(corpus_chrf.score, 2),
    }
    return {"segments": segments, "system": system}


def _get_comet():
    """Load and cache the COMET checkpoint (downloaded once)."""
    global _comet_model
    if _comet_model is not None:
        return _comet_model
    with _comet_lock:
        if _comet_model is None:
            from comet import download_model, load_from_checkpoint

            path = download_model(_COMET_MODEL_ID)
            _comet_model = load_from_checkpoint(path)
    return _comet_model


def comet_scores(srcs: list[str], hyps: list[str], refs: list[str]) -> dict:
    """Reference-based COMET. Returns {"segments": [float], "system": float}."""
    model = _get_comet()
    data = [
        {"src": s, "mt": m, "ref": r} for s, m, r in zip(srcs, hyps, refs)
    ]
    gpus = 1 if _COMET_DEVICE == "cuda" else 0
    output = model.predict(data, batch_size=8, gpus=gpus, progress_bar=False)
    scores = [round(float(x), 4) for x in output.scores]
    return {"segments": scores, "system": round(float(output.system_score), 4)}


def score(segments: list[dict], want_comet: bool = False) -> dict:
    """Score a batch of {src, mt, ref} segments for one model.

    Always computes BLEU + ChrF++ (if sacrebleu is present); adds COMET only
    when requested and installed. A failing metric is reported in `errors`
    rather than aborting the whole run.
    """
    avail = available()
    srcs = [seg.get("src", "") for seg in segments]
    hyps = [seg.get("mt", "") for seg in segments]
    refs = [seg.get("ref", "") for seg in segments]

    result: dict = {
        "available": avail,
        "comet_model": _COMET_MODEL_ID if (want_comet and avail["comet"]) else None,
        "segments": [{} for _ in segments],
        "system": {},
        "errors": {},
    }

    if avail["sacrebleu"]:
        try:
            lex = lexical_scores(hyps, refs)
            for slot, seg in zip(result["segments"], lex["segments"]):
                slot.update(seg)
            result["system"].update(lex["system"])
        except Exception as e:  # never abort the bench on a metric error
            result["errors"]["lexical"] = str(e)
    else:
        result["errors"]["lexical"] = "sacrebleu not installed"

    if want_comet:
        if avail["comet"]:
            try:
                cm = comet_scores(srcs, hyps, refs)
                for slot, val in zip(result["segments"], cm["segments"]):
                    slot["comet"] = val
                result["system"]["comet"] = cm["system"]
            except Exception as e:
                result["errors"]["comet"] = str(e)
        else:
            result["errors"]["comet"] = "unbabel-comet not installed"

    return result
