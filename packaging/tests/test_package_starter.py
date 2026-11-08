#!/usr/bin/env python3
"""Packager tests. Synthetic fixtures plus one local archive of this repo.

Nothing here publishes a download or certifies Premiere on a Mac.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PIN = "7557eeeedab3dd444effa27474cbaad23ace997e"
CORE_FILES = (
    "setup.sh",
    "setup-premiere.sh",
    "check-setup.sh",
    "finalize.sh",
    "lanes/premiere/premiere-bridge.mjs",
    "lanes/premiere/premiere-up.sh",
    "lanes/premiere/audio-polish.py",
    "lanes/premiere/joint-fades.py",
    "lanes/premiere/grade-lut.py",
)


def load_packager():
    path = ROOT / "packaging" / "package_starter.py"
    spec = importlib.util.spec_from_file_location("package_starter", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["package_starter"] = module
    spec.loader.exec_module(module)
    return module


MOD = load_packager()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class FixtureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.audit = {
            "assets": [
                {
                    "path": "assets/fonts/Inter-Regular.otf",
                    "decision": "allow",
                    "license_file": "assets/fonts/OFL-Inter.txt",
                    "license_marker": "SIL OPEN FONT LICENSE",
                },
                {
                    "path": "assets/fonts/Coolvetica-Rg.otf",
                    "decision": "deny",
                    "reason": "no license file",
                },
            ]
        }
        self.profile = {
            "name": "fixture",
            "packager_version": "1",
            "pinned_commit": "a" * 40,
            "commit_policy": "explicit",
            "allow_entire_tree": True,
            "required": ["setup.sh", "lanes/premiere/premiere-bridge.mjs"],
            "overlays": {},
        }
        write(self.root / "setup.sh", "echo setup\n")
        write(self.root / "lanes/premiere/premiere-bridge.mjs", "export const bridge = 1;\n")
        write(self.root / "assets/fonts/OFL-Inter.txt", "SIL OPEN FONT LICENSE\n")
        write(self.root / "assets/fonts/Inter-Regular.otf", "inter-bytes")
        write(self.root / "assets/fonts/Coolvetica-Rg.otf", "coolvetica-bytes")
        write(self.root / "notes.txt", "hello\n")

    def tearDown(self):
        self.tmp.cleanup()

    def assemble(self, commit=None):
        return MOD.assemble(
            self.root,
            self.profile,
            MOD.index_audit(self.audit),
            source_commit=commit or ("a" * 40),
        )

    def test_exclusions_and_licensed_font(self):
        secret = "ghp_" + ("a" * 24)
        write(self.root / "projects/client-job/raw/clip.mp4", "media")
        write(self.root / "projects/client-job/notes.txt", "job")
        write(self.root / ".git/config", "git metadata " + secret)
        write(self.root / "node_modules/pkg/index.js", "module")
        write(self.root / ".env", "TOKEN=" + secret + "\n")
        write(self.root / ".mcp.json", "{\"mcpServers\":{}}\n")
        write(self.root / ".setup-complete", "lane=premiere\n")
        write(self.root / ".setup-hyperframes-ok", "ok\n")
        write(self.root / "presets/road-to-20k/tools/place.py", "personal preset\n")
        write(self.root / "assets/sfx/boom.mp3", "sfx")
        write(self.root / "assets/luts/rec709/Autumn.cube", "LUT\n")
        write(self.root / "vendor/premiere-mcp/dist/index.js", "vendor")
        write(self.root / "debug.log", "log")
        write(self.root / "outputs/final.mp4", "out")
        assembly = self.assemble()
        paths = assembly.paths()
        self.assertIn("setup.sh", paths)
        self.assertIn("assets/fonts/Inter-Regular.otf", paths)
        self.assertIn("assets/fonts/OFL-Inter.txt", paths)
        self.assertNotIn("assets/fonts/Coolvetica-Rg.otf", paths)
        blob = b"\n".join(data for _, data in assembly.members)
        self.assertNotIn(secret.encode(), blob)
        for path in paths:
            self.assertFalse(path.startswith("projects/"))
            self.assertFalse(path.startswith(".git/"))
            self.assertFalse(path.startswith("node_modules/"))
            self.assertFalse(path.startswith("presets/road-to-20k/"))
            self.assertFalse(path.startswith("assets/sfx/"))
            self.assertFalse(path.startswith("assets/luts/"))
            self.assertFalse(path.startswith("vendor/"))
            self.assertFalse(path.startswith("outputs/"))
            self.assertNotEqual(path, ".env")
            self.assertNotEqual(path, ".mcp.json")
            self.assertFalse(path.endswith(".mp4"))
            self.assertFalse(path.endswith(".log"))
        reasons = dict(assembly.excluded)
        self.assertIn("assets/fonts/Coolvetica-Rg.otf", reasons)

    def test_secret_in_included_file_fails_without_echoing_it(self):
        token = "ghp_" + ("b" * 24)
        write(self.root / "notes.txt", "token = " + token + "\n")
        with self.assertRaises(MOD.PackageError) as caught:
            self.assemble()
        self.assertNotIn(token, str(caught.exception))
        self.assertIn("secret", str(caught.exception))

    def test_assigned_secret_and_home_path(self):
        write(self.root / "notes.txt", "API_TOKEN=abcd1234efgh\n")
        with self.assertRaises(MOD.PackageError) as caught:
            self.assemble()
        self.assertIn("assigned secret", str(caught.exception))
        self.assertNotIn("abcd1234efgh", str(caught.exception))

        write(self.root / "notes.txt", "see /Users/exampleperson/Desktop/clip.mov\n")
        with self.assertRaises(MOD.PackageError) as caught:
            self.assemble()
        self.assertIn("personal home path", str(caught.exception))

        write(self.root / "notes.txt", "library at /Users/Shared/video-editor-luts\n")
        assembly = self.assemble()
        self.assertIn("notes.txt", assembly.paths())

    def test_missing_required_file_writes_nothing(self):
        (self.root / "setup.sh").unlink()
        with self.assertRaises(MOD.PackageError) as caught:
            self.assemble()
        self.assertIn("missing required file setup.sh", str(caught.exception))
        out = self.root / "out.zip"
        code = MOD.main(
            [
                "--source",
                str(self.root),
                "--profile",
                self._write_profile(),
                "--license-audit",
                self._write_audit(),
                "--source-commit",
                "a" * 40,
                "pack",
                "--output",
                str(out),
            ]
        )
        self.assertEqual(code, 2)
        self.assertFalse(out.exists())

    def test_commit_mismatch(self):
        with self.assertRaises(MOD.PackageError):
            self.assemble(commit="b" * 40)

    def test_license_marker_required(self):
        write(self.root / "assets/fonts/OFL-Inter.txt", "not a license\n")
        with self.assertRaises(MOD.PackageError) as caught:
            self.assemble()
        self.assertIn("license marker", str(caught.exception))

    def test_symlink_refused(self):
        outside = self.root / "outside-secret.txt"
        write(outside, "secret-outside")
        link = self.root / "linked.txt"
        link.symlink_to(outside)
        with self.assertRaises(MOD.PackageError) as caught:
            self.assemble()
        self.assertIn("symlink", str(caught.exception))
        self.assertNotIn("secret-outside", str(caught.exception))

    def test_manifest_checksum_and_deterministic_zip(self):
        assembly = self.assemble()
        first = MOD.archive_bytes(assembly)
        second = MOD.archive_bytes(assembly)
        self.assertEqual(first, second)
        out_a = self.root / "a.zip"
        out_b = self.root / "b.zip"
        MOD.write_zip(first, out_a)
        MOD.write_zip(second, out_b)
        self.assertEqual(out_a.read_bytes(), out_b.read_bytes())
        with zipfile.ZipFile(out_a) as archive:
            names = archive.namelist()
            self.assertEqual(names, sorted(names))
            payload = {name: archive.read(name) for name in names}
        manifest = json.loads(payload["MANIFEST.json"])
        self.assertEqual(manifest["distribution"], "not-released")
        self.assertEqual(manifest["pinned_commit"], "a" * 40)
        sums = {}
        for line in payload["SHA256SUMS"].decode().splitlines():
            digest, path = line.split("  ", 1)
            sums[path] = digest
        self.assertNotIn("SHA256SUMS", sums)
        for item in manifest["files"]:
            self.assertEqual(sums[item["path"]], MOD._sha256(payload[item["path"]]))
            self.assertEqual(item["sha256"], MOD._sha256(payload[item["path"]]))
        self.assertEqual(sums["MANIFEST.json"], MOD._sha256(payload["MANIFEST.json"]))
        self.assertEqual(sums["VERSION"], MOD._sha256(payload["VERSION"]))
        self.assertIn(b"distribution=not-released", payload["VERSION"])

    def _write_profile(self) -> str:
        path = self.root / "profile.json"
        path.write_text(json.dumps(self.profile), encoding="utf-8")
        return str(path)

    def _write_audit(self) -> str:
        path = self.root / "audit.json"
        path.write_text(json.dumps(self.audit), encoding="utf-8")
        return str(path)


class RealTreeTest(unittest.TestCase):
    def test_profile_is_allowlist_not_wholesale(self):
        profile = json.loads((ROOT / "packaging" / "starter-profile.json").read_text())
        self.assertFalse(profile.get("allow_entire_tree"))
        self.assertNotIn("", profile["allow_prefixes"])
        for core in CORE_FILES:
            self.assertNotIn(core, profile["pin_exempt_files"])
            self.assertTrue(any(core.startswith(prefix) or core in profile["allow_files"] for prefix in profile["allow_prefixes"]) or core in profile["allow_files"])
        self.assertIn("presets/road-to-20k/", profile["extra_deny_prefixes"])

    def test_only_expected_paths_differ_from_pin(self):
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", PIN],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        unexpected = []
        for line in proc.stdout.splitlines():
            if line.startswith("packaging/"):
                continue
            if line in {".gitignore", "RELEASE.md"}:
                continue
            unexpected.append(line)
        self.assertEqual(unexpected, [])

    def test_core_bytes_match_pin_and_archive_is_clean(self):
        for rel in CORE_FILES:
            blob = subprocess.run(
                ["git", "-C", str(ROOT), "cat-file", "blob", f"{PIN}:{rel}"],
                check=True,
                stdout=subprocess.PIPE,
            ).stdout
            self.assertEqual(blob, (ROOT / rel).read_bytes(), rel)

        profile = json.loads((ROOT / "packaging" / "starter-profile.json").read_text())
        audit = MOD.index_audit(json.loads((ROOT / "packaging" / "license-audit.json").read_text()))
        assembly = MOD.assemble(ROOT, profile, audit)
        paths = assembly.paths()
        for rel in (
            "setup.sh",
            "setup-premiere.sh",
            "lanes/premiere/premiere-bridge.mjs",
            "lanes/premiere/premiere-up.sh",
            "finalize.sh",
        ):
            self.assertIn(rel, paths)
        self.assertIn("START-HERE.md", paths)
        self.assertIn("assets/fonts/Inter-Regular.otf", paths)
        self.assertIn("assets/fonts/OFL-Inter.txt", paths)
        self.assertIn("assets/fonts/OFL-TikTokSans.txt", paths)
        forbidden_parts = (
            "projects/",
            "presets/road-to-20k/",
            "assets/sfx/",
            "assets/luts/",
            "assets/models/",
            ".git/",
            "node_modules/",
            "vendor/",
            "packaging/tests/",
            "packaging/dist/",
        )
        for path in paths:
            for part in forbidden_parts:
                self.assertFalse(path.startswith(part), path)
            self.assertNotIn(path, {".env", ".mcp.json", ".setup-complete"})
        for denied in (
            "assets/fonts/Coolvetica-Rg.otf",
            "assets/fonts/PlayfairDisplay-Italic-VF.ttf",
            "lanes/premiere/premiere-templates/adjustment-layer.prproj",
        ):
            self.assertNotIn(denied, paths)
        placeholder = dict(assembly.members)[".mcp.json.example"]
        self.assertIn(b"does not claim Windows", placeholder)
        self.assertNotIn(b"Windows both fully supported", placeholder)
        self.assertNotIn(b"/Users/creator", placeholder)
        self.assertIn(b'"PREMIERE_MCP_TELEMETRY": "0"', placeholder)

        payload_a = MOD.archive_bytes(assembly)
        payload_b = MOD.archive_bytes(assembly)
        self.assertEqual(payload_a, payload_b)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "starter.zip"
            MOD.write_zip(payload_a, out)
            with zipfile.ZipFile(out) as archive:
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                manifest = json.loads(archive.read("MANIFEST.json"))
                version = archive.read("VERSION")
            self.assertEqual(manifest["distribution"], "not-released")
            self.assertEqual(manifest["content_matches_commit"], PIN)
            self.assertEqual(manifest["working_head"], subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip())
            self.assertIn(b"distribution=not-released", version)
            self.assertGreater(len(manifest["files"]), 20)
            self.assertLess(len(manifest["files"]), 5000)


class GateTest(unittest.TestCase):
    def test_example_record_is_not_a_pass(self):
        code = subprocess.run(
            [
                "python3",
                str(ROOT / "packaging/gates/check_mac_smoke.py"),
                str(ROOT / "packaging/gates/smoke-record.example.json"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(code.returncode, 2)
        self.assertIn("Do not record a download", code.stderr)

    def test_ship_refuses_with_and_without_a_record(self):
        script = ROOT / "packaging/delivery/ship.sh"
        text = script.read_text(encoding="utf-8")
        for banned in ("curl", "wget", "wrangler", "ssh ", "nc "):
            self.assertNotIn(banned, text)
        missing = subprocess.run(["bash", str(script), "/tmp/does-not-exist-smoke.json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(missing.returncode, 3)
        self.assertIn("refusing to publish", missing.stdout)

        record = {
            "pinned_commit": PIN,
            "premiere_version_reported": "25.6.2",
            "runner": "mac-smoke",
            "grading_note": "Bridge reported 25.6.2. Docs measured 26.3.2. Grade is unverified.",
            "grade_lut_replay_verified": False,
            "multi_editor_parity_claimed": False,
            "linux_ci_certifies_mac": False,
            "download_published": False,
            "gates": {},
        }
        spec = importlib.util.spec_from_file_location(
            "check_mac_smoke", ROOT / "packaging/gates/check_mac_smoke.py"
        )
        checker = importlib.util.module_from_spec(spec)
        sys.modules["check_mac_smoke"] = checker
        spec.loader.exec_module(checker)
        record["gates"] = {name: "passed" for name in checker.REQUIRED_GATES}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            ok = subprocess.run(
                ["python3", str(ROOT / "packaging/gates/check_mac_smoke.py"), str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("Publication stays disabled", ok.stdout)
            refused = subprocess.run(
                ["bash", str(script), str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(refused.returncode, 3)
            self.assertIn("refusing to publish", refused.stdout)

        record["grade_lut_replay_verified"] = True
        errors = checker.validate(record)
        self.assertTrue(any("grade_lut" in item for item in errors))
        record["grade_lut_replay_verified"] = False
        record["runner"] = "/Users/exampleperson/smoke"
        errors = checker.validate(record)
        self.assertTrue(any("home path" in item for item in errors))

    def test_lane_and_publish_flags(self):
        script = str(ROOT / "packaging/package-for-client.sh")
        publish = subprocess.run(["bash", script, "--publish"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(publish.returncode, 2)
        lane = subprocess.run(["bash", script, "--lane", "resolve", "plan"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(lane.returncode, 2)
        self.assertIn("Premiere on macOS only", lane.stderr)
        bare = subprocess.run(["bash", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(bare.returncode, 2)
        self.assertFalse(list((ROOT / "packaging").glob("dist/*.zip")))


class SampleTest(unittest.TestCase):
    def test_synthetic_sample_stays_out_of_job_folders(self):
        script = str(ROOT / "packaging/sample/make-synthetic-sample.sh")
        refused = subprocess.run(
            ["bash", script, str(ROOT / "projects/synthetic-smoke/raw/clip.mp4")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(refused.returncode, 2)
        self.assertFalse((ROOT / "projects").exists())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "synthetic-sample.mp4"
            made = subprocess.run(
                ["bash", script, str(out)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            self.assertGreater(float(probe.stdout.strip()), 1.0)


if __name__ == "__main__":
    unittest.main()
