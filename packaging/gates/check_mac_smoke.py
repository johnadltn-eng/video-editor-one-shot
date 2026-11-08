#!/usr/bin/env python3
"""Validate a local Mac smoke-test record.

A passing record is a human gate on a Mac with Premiere. It is not produced
by Linux tests, and it does not authorize publication. This starter's
packager version still requires grading to stay unverified: the LUT library
is not in the archive, and the captured grade was measured on Premiere 26.3.2.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_GATES = (
    "clean_unpack_exclusions",
    "dependencies_present",
    "setup_sh_completed",
    "premiere_lane_setup_completed",
    "bridge_ping_recorded",
    "premiere_version_recorded",
    "synthetic_or_self_recorded_only",
    "timeline_replay",
    "export_ffprobe",
)

PINNED_COMMIT = "7557eeeedab3dd444effa27474cbaad23ace997e"


def _home_path(value: str) -> bool:
    text = value.replace("\\", "/")
    if "/Users/" in text and "/Users/Shared" not in text and "/Users/Public" not in text:
        return True
    if "/home/" in text:
        return True
    return False


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    if record.get("pinned_commit") != PINNED_COMMIT:
        errors.append("pinned_commit does not match the starter pin")
    if record.get("linux_ci_certifies_mac") is not False:
        errors.append("linux_ci_certifies_mac must be false")
    if record.get("multi_editor_parity_claimed") is not False:
        errors.append("multi_editor_parity_claimed must be false")
    if record.get("download_published") is not False:
        errors.append("download_published must be false")
    if record.get("parity_certified") is not False:
        errors.append("parity_certified must stay false until the Mac same-footage gate is actually run")
    if record.get("grade_lut_replay_verified") is not False:
        errors.append("grade_lut_replay_verified must stay false for this starter")
    version = str(record.get("premiere_version_reported") or "").strip()
    if not version:
        errors.append("premiere_version_reported is empty")
    note = str(record.get("grading_note") or "")
    if "unverified" not in note.lower():
        errors.append("grading_note must say the version-specific grade is unverified")
    if version and version != "26.3.2" and "26.3.2" not in note:
        errors.append("a non-26.3.2 Premiere build must name 26.3.2 as the measured docs version")
    runner = str(record.get("runner") or "").strip()
    if not runner:
        errors.append("runner is empty")
    elif _home_path(runner):
        errors.append("runner must not be a home path")
    gates = record.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates must be an object")
        gates = {}
    for name in REQUIRED_GATES:
        if gates.get(name) != "passed":
            errors.append(f"gate {name} is not passed")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a local Mac smoke record. Does not publish.")
    parser.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    if not args.record.is_file():
        print(f"ERROR: no mac smoke record at {args.record}", file=sys.stderr)
        print("Do not record a download or a successful setup.", file=sys.stderr)
        return 2
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("ERROR: smoke record is not JSON", file=sys.stderr)
        return 2
    if not isinstance(record, dict):
        print("ERROR: smoke record must be an object", file=sys.stderr)
        return 2
    errors = validate(record)
    if errors:
        print("ERROR: mac smoke gates are not satisfied:", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        print("Do not record a download or a successful setup.", file=sys.stderr)
        return 2
    print("Mac smoke gates are recorded locally. Publication stays disabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
