#!/usr/bin/env python
"""CLI to convert registered models to CTranslate2 format.

Usage:
  python -m scripts.convert_model --list
  python -m scripts.convert_model qwen3-4b
  python -m scripts.convert_model gemma3-4b-it --quantization float16 --force
  python -m scripts.convert_model --all
"""
from __future__ import annotations

import argparse
import sys

from app.config import settings
from app.converter import convert, is_converted


def main() -> int:
    p = argparse.ArgumentParser(description="Convert HF models to CTranslate2.")
    p.add_argument("key", nargs="?", help="Registry key to convert.")
    p.add_argument("--all", action="store_true", help="Convert all supported models.")
    p.add_argument("--list", action="store_true", help="List registry and exit.")
    p.add_argument("--quantization", help="int8_float16 | float16 | int8 | float32")
    p.add_argument("--force", action="store_true", help="Reconvert if it exists.")
    args = p.parse_args()

    if args.list or (not args.key and not args.all):
        for s in settings.registry.values():
            flag = "ok " if s.supported else "NO "
            conv = "converted" if is_converted(s.key) else "-"
            print(f"[{flag}] {s.key:22} {s.hf_id:32} {conv}  {s.note}")
        return 0

    keys = (
        [s.key for s in settings.registry.values() if s.supported]
        if args.all
        else [args.key]
    )
    for key in keys:
        try:
            out = convert(key, quantization=args.quantization, force=args.force)
            print(f"[done] {key} -> {out}")
        except Exception as e:
            print(f"[fail] {key}: {e}", file=sys.stderr)
            if not args.all:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
