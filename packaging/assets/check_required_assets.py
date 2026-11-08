#!/usr/bin/env python3
"""Report asset gaps. Does not download, purchase, or copy files into the archive.

Exit 2 while any blocked asset is still blocked. That is the missing-dependency
gate. A green packaging test does not clear it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = Path(__file__).resolve().parent / "required-assets.json"


def main() -> int:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    blocked = [row for row in spec["assets"] if str(row.get("status", "")).startswith("blocked")]
    if not blocked:
        print("no blocked assets recorded")
        return 0
    print("missing-dependency gate: these features are not fully supplied")
    for row in blocked:
        present = (ROOT / row["path"]).is_file()
        print(f"- {row['id']}: {row['feature']}")
        print(f"  status={row['status']} source_present={present}")
        print(f"  {row['reason']}")
    print("Do not treat the archive as full asset parity.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
