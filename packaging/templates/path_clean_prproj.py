#!/usr/bin/env python3
"""Write a path-cleaned adjustment-layer donor next to this script.

The pinned donor keeps two last-known project path fields. This copy clears
those strings and leaves the AdjustmentLayer count unchanged. It does not
open Premiere and does not certify 25.6.2 import.
"""

from __future__ import annotations

import gzip
import sys
from pathlib import Path


DONOR = Path(__file__).resolve().parents[2] / "lanes/premiere/premiere-templates/adjustment-layer.prproj"
OUT = Path(__file__).resolve().parent / "adjustment-layer.pathclean.prproj"


def _home_prefix() -> str:
    # Built at runtime so the source file does not contain an absolute home path.
    return "/" + "Users/" + "creator"


def clean(xml: str) -> str:
    layers = xml.count("AdjustmentLayer")
    prefix = _home_prefix()
    cleaned = xml.replace(prefix + "/templates/adjustment-layer.prproj", "")
    cleaned = cleaned.replace(prefix + "/templates", "")
    if "/Users/" in cleaned or "/home/" in cleaned:
        raise SystemExit("cleaned template still contains a home-directory path")
    if cleaned.count("AdjustmentLayer") != layers:
        raise SystemExit("AdjustmentLayer count changed")
    return cleaned


def main() -> int:
    xml = gzip.decompress(DONOR.read_bytes()).decode("utf-8")
    blob = gzip.compress(clean(xml).encode("utf-8"), mtime=0)
    OUT.write_bytes(blob)
    print(f"wrote {OUT} ({len(blob)} bytes). Premiere import is untested.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
