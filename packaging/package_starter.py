#!/usr/bin/env python3
"""Allowlist packager for a local Premiere-on-macOS starter archive.

The archive is a review artifact. This tool does not upload it, open a
download page, or mark a setup as certified. Linux runs of the unit tests
do not certify macOS or Premiere.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


PACKAGER_VERSION = "1"
DISTRIBUTION = "not-released"

# Engine denylist. A profile allow prefix cannot override these.
DENY_DIR_NAMES = {
    ".git",
    ".cache",
    ".wrangler",
    "__pycache__",
    "node_modules",
    "vendor",
    "cartoon-refs",
}
DENY_PREFIXES = (
    "projects/",
    "outputs/",
    "packaging/dist/",
    "packaging/tests/",
    "packaging/sample/out/",
    "packaging/gates/records/",
)
DENY_FILENAMES = {
    ".env",
    ".mcp.json",
    ".setup-complete",
    ".setup-hyperframes-ok",
    ".ds_store",
    "id_rsa",
    "id_dsa",
    "credentials.json",
}
# Filename prefixes that are secret files, with one explicit exception.
DENY_FILENAME_PREFIXES = (".env.",)
DENY_FILENAME_PREFIX_EXCEPTIONS = {".env.example"}
DENY_SUFFIXES = {
    ".log",
    ".pem",
    ".p12",
    ".key",
    ".mp4",
    ".m4v",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".mp3",
    ".wav",
    ".aif",
    ".aiff",
    ".flac",
    ".cube",
    ".lookparams",
    ".lutparams",
    ".onnx",
    ".woff",
    ".woff2",
    ".otf",
    ".ttf",
    ".epr",
    ".drp",
    ".prproj",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".zip",
}
# Suffixes that stay excluded unless the license audit allows that exact path.
LICENSE_GATED_SUFFIXES = DENY_SUFFIXES - {".log", ".pem", ".p12", ".key", ".zip"}

# Home-directory paths. /Users/Shared and /Users/Public are machine-wide, not a person.
_HOME = re.compile(
    r"(?:(?<![A-Za-z0-9])/(?:Users|home)/)"
    r"(?!Shared\b|Public\b)"
    r"[A-Za-z0-9._-]{1,64}"
)
_WIN_HOME = re.compile(
    r"[A-Za-z]:[\\/]Users[\\/](?!Shared\b|Public\b)[A-Za-z0-9._-]+",
    re.IGNORECASE,
)
_SECRET_MARKERS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)
_ASSIGNED_SECRET = re.compile(
    r"(?im)^[ \t]*(?:export[ \t]+)?([A-Za-z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Za-z0-9_]*)"
    r"[ \t]*=[ \t]*['\"]?([^\s'\"]+)"
)
_PLACEHOLDER_VALUES = {
    "",
    "0",
    "false",
    "changeme",
    "example",
    "your-token",
    "your_token",
    "todo",
    "<<secret>>",
}

MANIFEST_NOTES = [
    "Local review archive only. Not a download release and not a Mac parity certification.",
    "Pinned editor bytes match the recorded source commit. Provenance lists reviewed additions.",
    "The feature target is the full source editor, including series tools. Parity is not claimed.",
    "Premiere grading notes measured on 26.3.2 are unverified on 25.6.2.",
    "Linux tests do not certify macOS, Premiere, Resolve, CapCut, or export.",
    "CinePacks LUTs, the SFX library, and Coolvetica are withheld. Missing-asset gates stay open.",
    "The adjustment-layer member is a path-cleaned derivative. Premiere import is untested.",
]


class PackageError(Exception):
    """The archive must not be written."""


@dataclass
class Assembly:
    profile_name: str
    packager_version: str
    pinned_commit: str
    working_head: str
    members: list[tuple[str, bytes]] = field(default_factory=list)
    excluded: list[tuple[str, str]] = field(default_factory=list)

    def paths(self) -> set[str]:
        return {path for path, _ in self.members}


def _posix(path: Path) -> str:
    text = path.as_posix()
    if text.startswith("./"):
        text = text[2:]
    return text


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise PackageError(f"{path} must be a JSON object")
    return data


def git_output(repo: Path, args: list[str]) -> bytes | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def working_head(repo: Path) -> str | None:
    raw = git_output(repo, ["rev-parse", "HEAD"])
    if raw is None:
        return None
    return raw.decode().strip()


def blob_at(repo: Path, commit: str, relpath: str) -> bytes | None:
    return git_output(repo, ["cat-file", "blob", f"{commit}:{relpath}"])


def _is_exempt(relpath: str, profile: dict) -> bool:
    if relpath in set(profile.get("pin_exempt_files") or []):
        return True
    for prefix in profile.get("pin_exempt_prefixes") or []:
        if relpath == prefix.rstrip("/") or relpath.startswith(prefix):
            return True
    return False


def _filename_denied(name: str) -> str | None:
    lower = name.lower()
    if lower in DENY_FILENAMES:
        return f"denied filename {name}"
    if lower.startswith(DENY_FILENAME_PREFIXES) and lower not in DENY_FILENAME_PREFIX_EXCEPTIONS:
        if lower.startswith(".env"):
            return "denied env file"
    if lower.endswith(".log"):
        return "denied log file"
    return None


def _prefix_denied(relpath: str) -> str | None:
    for prefix in DENY_PREFIXES:
        if relpath == prefix.rstrip("/") or relpath.startswith(prefix):
            return f"denied prefix {prefix}"
    parts = relpath.split("/")
    for part in parts[:-1]:
        if part in DENY_DIR_NAMES or part.lower() in DENY_DIR_NAMES:
            return f"denied directory {part}"
    return None


def _license_decision(relpath: str, audit: dict) -> dict | None:
    exact = audit.get("by_path", {}).get(relpath)
    if exact:
        return exact
    for prefix, entry in audit.get("by_prefix", {}).items():
        if relpath == prefix.rstrip("/") or relpath.startswith(prefix):
            return entry
    return None


def exclusion_reason(relpath: str, audit: dict) -> str | None:
    if relpath.startswith("/") or relpath.startswith("../") or "/../" in relpath or relpath == "..":
        return "path escapes the archive root"
    reason = _prefix_denied(relpath)
    if reason:
        return reason
    name = relpath.rsplit("/", 1)[-1]
    reason = _filename_denied(name)
    if reason:
        return reason
    suffix = Path(name).suffix.lower()
    if suffix in DENY_SUFFIXES:
        decision = _license_decision(relpath, audit)
        if suffix in LICENSE_GATED_SUFFIXES and decision and decision.get("decision") == "allow":
            return None
        if decision and decision.get("decision") == "deny":
            return decision.get("reason") or "license audit deny"
        return f"denied suffix {suffix}"
    decision = _license_decision(relpath, audit)
    if decision and decision.get("decision") == "deny":
        return decision.get("reason") or "license audit deny"
    return None


def profile_allows(relpath: str, profile: dict) -> bool:
    if profile.get("allow_entire_tree"):
        if profile.get("name") in {"premiere-mac-starter", "full-editor"}:
            raise PackageError("the editor profile must not allow the entire tree")
        return True
    allow_files = set(profile.get("allow_files") or [])
    if relpath in allow_files:
        return True
    for prefix in profile.get("allow_prefixes") or []:
        if not prefix:
            raise PackageError("empty allow prefix")
        if relpath == prefix.rstrip("/") or relpath.startswith(prefix):
            return True
    extra = profile.get("extra_deny_prefixes") or []
    for prefix in extra:
        if relpath == prefix.rstrip("/") or relpath.startswith(prefix):
            return False
    return False


def profile_extra_deny(relpath: str, profile: dict) -> str | None:
    for prefix in profile.get("extra_deny_prefixes") or []:
        if relpath == prefix.rstrip("/") or relpath.startswith(prefix):
            return f"profile deny {prefix}"
    return None


def scan_bytes(relpath: str, data: bytes) -> list[str]:
    """Return safeguard findings. Values of secrets are not included."""
    findings: list[str] = []
    if data.startswith(b"\x1f\x8b"):
        try:
            data = gzip.decompress(data)
        except gzip.BadGzipFile:
            return [f"{relpath}: unreadable gzip"]
    text = data.decode("utf-8", "ignore")
    for pattern in _SECRET_MARKERS:
        if pattern.search(text):
            findings.append(f"{relpath}: secret pattern")
            break
    for match in _ASSIGNED_SECRET.finditer(text):
        value = match.group(2).strip()
        if value.lower() in _PLACEHOLDER_VALUES or "example" in value.lower():
            continue
        if value.startswith("<<") or any(ch in value for ch in ".($<{[/\\"):
            continue
        if len(value) < 8 or not any(char.isdigit() for char in value):
            continue
        findings.append(f"{relpath}: assigned secret")
        break
    # Path scan on text. Binary fonts and other NUL-leading payloads are skipped
    # so compressed tables cannot false-positive, and those payloads are license-gated.
    if b"\x00" not in data[:1024]:
        if _HOME.search(text) or _WIN_HOME.search(text):
            findings.append(f"{relpath}: personal home path")
    return findings


def _check_license_companion(relpath: str, audit: dict, included: set[str], source: Path) -> None:
    decision = _license_decision(relpath, audit)
    if not decision or decision.get("decision") != "allow":
        return
    license_file = decision.get("license_file")
    marker = decision.get("license_marker")
    if not license_file or not marker:
        if decision.get("evidence") == "path-scanned-editor-file":
            return
        raise PackageError(f"{relpath} is allowed without a license file and marker")
    if license_file not in included:
        raise PackageError(f"{relpath} requires {license_file} in the archive")
    blob = (source / license_file).read_bytes()
    if marker.encode("utf-8") not in blob:
        raise PackageError(f"{license_file} is missing the required license marker")


def _iter_files(source: Path, profile: dict):
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        rel_dir = _posix(Path(dirpath).relative_to(source))
        if rel_dir == ".":
            rel_dir = ""
        kept = []
        for name in sorted(dirnames):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            child = Path(dirpath) / name
            if _prefix_denied(rel + "/"):
                continue
            if name in DENY_DIR_NAMES or name.lower() in DENY_DIR_NAMES:
                continue
            if child.is_symlink():
                if profile_allows(rel, profile) or profile.get("allow_entire_tree"):
                    raise PackageError(f"refusing symlink {rel}")
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            yield rel, Path(dirpath) / name


def index_provenance(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = load_json(path)
    indexed = {}
    for entry in data.get("files") or []:
        indexed[entry["path"]] = entry
    return indexed


def _matches_provenance(relpath: str, data: bytes, committed: bytes | None, provenance: dict) -> bool:
    entry = provenance.get(relpath)
    if not entry or entry.get("sha256") != _sha256(data):
        return False
    basis = entry.get("basis")
    if basis == "added":
        return committed is None
    if basis == "replaces-pinned":
        return committed is not None and committed != data
    return False


def assemble(source: Path, profile: dict, audit: dict, source_commit: str | None = None, provenance: dict | None = None) -> Assembly:
    source = source.resolve()
    pinned = str(profile.get("pinned_commit") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", pinned):
        raise PackageError("pinned_commit must be a 40-character hex sha")
    policy = profile.get("commit_policy")
    head = working_head(source)
    if policy == "tree_matches_pin":
        if head is None:
            raise PackageError("tree_matches_pin requires a git checkout")
        if source_commit and source_commit != pinned:
            raise PackageError("source commit does not match the pinned commit")
        recorded_head = head
    elif policy == "explicit":
        if source_commit != pinned:
            raise PackageError("explicit source commit does not match the pinned commit")
        recorded_head = head or "not-checked"
    else:
        raise PackageError(f"unknown commit_policy {policy!r}")
    if provenance is None and policy == "tree_matches_pin":
        provenance = index_provenance(source / "packaging" / "provenance.json")
    provenance = provenance or {}
    withheld = profile.get("withhold_files") or {}

    included: list[tuple[str, bytes]] = []
    excluded: list[tuple[str, str]] = []
    for rel, path in _iter_files(source, profile):
        if path.is_symlink():
            if profile_allows(rel, profile) and not _prefix_denied(rel):
                raise PackageError(f"refusing symlink {rel}")
            excluded.append((rel, "symlink"))
            continue
        if not path.is_file():
            continue
        if rel in withheld:
            if profile_allows(rel, profile) or profile.get("allow_entire_tree"):
                excluded.append((rel, withheld[rel]))
            continue
        extra = profile_extra_deny(rel, profile)
        reason = extra or exclusion_reason(rel, audit)
        if reason:
            # Only record exclusions the profile would otherwise have shipped,
            # so a whole-repo walk does not list every ignored media file.
            if profile_allows(rel, profile) or profile.get("allow_entire_tree"):
                excluded.append((rel, reason))
            continue
        if not profile_allows(rel, profile):
            continue
        data = path.read_bytes()
        if policy == "tree_matches_pin" and not _is_exempt(rel, profile):
            committed = blob_at(source, pinned, rel)
            if committed != data and not _matches_provenance(rel, data, committed, provenance):
                if committed is None:
                    raise PackageError(f"{rel} is not in the pinned commit and has no matching provenance entry")
                raise PackageError(f"{rel} differs from the pinned commit and has no matching provenance entry")
        findings = scan_bytes(rel, data)
        if findings:
            raise PackageError("safeguard failed: " + "; ".join(findings))
        included.append((rel, data))

    by_path = {path: data for path, data in included}
    for dest, src_rel in (profile.get("overlays") or {}).items():
        if Path(dest).is_absolute() or ".." in Path(dest).parts:
            raise PackageError(f"overlay destination escapes the archive: {dest}")
        overlay_path = source / src_rel
        if not overlay_path.is_file():
            raise PackageError(f"missing overlay source {src_rel}")
        data = overlay_path.read_bytes()
        findings = scan_bytes(dest, data)
        if findings:
            raise PackageError("safeguard failed: " + "; ".join(findings))
        by_path[dest] = data

    included_paths = set(by_path)
    for required in profile.get("required") or []:
        if required not in included_paths:
            raise PackageError(f"missing required file {required}")
    for rel in sorted(included_paths):
        _check_license_companion(rel, audit, included_paths, source)

    members = sorted(by_path.items())
    return Assembly(
        profile_name=str(profile["name"]),
        packager_version=str(profile.get("packager_version") or PACKAGER_VERSION),
        pinned_commit=pinned,
        working_head=recorded_head,
        members=members,
        excluded=sorted(excluded),
    )


def archive_bytes(assembly: Assembly) -> dict[str, bytes]:
    files = []
    for path, data in assembly.members:
        if path in {"VERSION", "MANIFEST.json", "SHA256SUMS"}:
            raise PackageError(f"{path} is reserved for generated archive metadata")
        files.append({"path": path, "bytes": len(data), "sha256": _sha256(data)})
    version = (
        f"profile={assembly.profile_name}\n"
        f"packager_version={assembly.packager_version}\n"
        f"pinned_commit={assembly.pinned_commit}\n"
        f"content_matches_commit={assembly.pinned_commit}\n"
        f"working_head={assembly.working_head}\n"
        f"distribution={DISTRIBUTION}\n"
    ).encode()
    manifest = {
        "content_matches_commit": assembly.pinned_commit,
        "distribution": DISTRIBUTION,
        "excluded": [{"path": path, "reason": reason} for path, reason in assembly.excluded],
        "files": files,
        "notes": list(MANIFEST_NOTES),
        "packager_version": assembly.packager_version,
        "pinned_commit": assembly.pinned_commit,
        "profile": assembly.profile_name,
        "working_head": assembly.working_head,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    lines = [f"{item['sha256']}  {item['path']}" for item in files]
    lines.append(f"{_sha256(version)}  VERSION")
    lines.append(f"{_sha256(manifest_bytes)}  MANIFEST.json")
    checksums = ("\n".join(lines) + "\n").encode()
    payload = {path: data for path, data in assembly.members}
    payload["VERSION"] = version
    payload["MANIFEST.json"] = manifest_bytes
    payload["SHA256SUMS"] = checksums
    return dict(sorted(payload.items()))


def write_zip(payload: dict[str, bytes], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path, data in payload.items():
                info = zipfile.ZipInfo(filename=path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.flag_bits = 0x800  # UTF-8 names
                mode = 0o755 if path.endswith(".sh") else 0o644
                info.external_attr = mode << 16
                archive.writestr(info, data)
        os.replace(temporary, output)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def index_audit(audit: dict) -> dict:
    by_path = {}
    by_prefix = {}
    for entry in audit.get("assets") or []:
        path = entry.get("path")
        if not path:
            raise PackageError("license audit entry is missing path")
        if path.endswith("/"):
            by_prefix[path] = entry
        else:
            by_path[path] = entry
    return {"by_path": by_path, "by_prefix": by_prefix, "raw": audit}


def _output_allowed(path: Path) -> None:
    resolved = path.resolve()
    parts = resolved.parts
    if "projects" in parts:
        raise PackageError("refusing to write an archive inside projects/")
    if ".git" in parts:
        raise PackageError("refusing to write an archive inside git metadata")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local allowlisted starter archive. Does not publish.")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--profile", type=Path, default=None)
    parser.add_argument("--license-audit", type=Path, default=None)
    parser.add_argument("--source-commit", default=None)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("plan", help="print the file plan; write nothing")
    pack = sub.add_parser("pack", help="write a local zip")
    pack.add_argument("--output", type=Path, required=True)
    return parser


def _load(args: argparse.Namespace) -> tuple[Path, dict, dict]:
    source = args.source.resolve()
    profile_path = args.profile or (source / "packaging" / "starter-profile.json")
    audit_path = args.license_audit or (source / "packaging" / "license-audit.json")
    if not profile_path.is_file():
        raise PackageError(f"missing profile {profile_path}")
    if not audit_path.is_file():
        raise PackageError(f"missing license audit {audit_path}")
    return source, load_json(profile_path), index_audit(load_json(audit_path))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command not in {"plan", "pack"}:
        parser.print_help(sys.stderr)
        print("\nRefusing to pack without an explicit plan or pack command.", file=sys.stderr)
        return 2
    try:
        source, profile, audit = _load(args)
        assembly = assemble(source, profile, audit, source_commit=args.source_commit)
        if args.command == "plan":
            for path, _ in assembly.members:
                print(path)
            print(f"# members {len(assembly.members)} excluded {len(assembly.excluded)}", file=sys.stderr)
            return 0
        _output_allowed(args.output)
        if args.output.exists():
            raise PackageError(f"refusing to overwrite {args.output}")
        payload = archive_bytes(assembly)
        write_zip(payload, args.output)
        print(f"wrote local archive {args.output} ({len(payload)} members, {DISTRIBUTION})")
        print("This file is not a release and was not published.")
        return 0
    except PackageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
