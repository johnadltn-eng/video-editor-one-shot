#!/usr/bin/env python3
"""Regression checks for reviewed local tools. No Premiere and no project writes."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_tool(relative: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / relative), *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class ToolSafetyTest(unittest.TestCase):
    def test_grade_and_media_fix_do_not_apply_by_default(self):
        grade = run_tool("presets/road-to-20k/tools/grade.py", "example-job")
        self.assertNotEqual(grade.returncode, 0)
        self.assertIn("dry-run", grade.stderr + grade.stdout)
        self.assertIn("--apply", grade.stderr + grade.stdout)

        media = run_tool("presets/road-to-20k/tools/media_fix.py", "example-job", "blur", "clip.mov")
        self.assertNotEqual(media.returncode, 0)
        self.assertIn("dry-run", media.stderr + media.stdout)
        self.assertIn("--move-original", media.stderr + media.stdout)

    def test_move_and_close_stay_behind_flags(self):
        media = (ROOT / "presets/road-to-20k/tools/media_fix.py").read_text(encoding="utf-8")
        move_at = media.index("shutil.move")
        self.assertIn("--move-original", media[max(0, move_at - 500):move_at])
        grade = (ROOT / "presets/road-to-20k/tools/grade.py").read_text(encoding="utf-8")
        self.assertLess(grade.index('"--apply"'), grade.index("shutil.copy"))
        self.assertLess(grade.index('"--apply"'), grade.index("p.closeDocument"))
        place = (ROOT / "presets/road-to-20k/tools/place.py").read_text(encoding="utf-8")
        self.assertIn("/fx/outputs/", place)
        self.assertLess(place.index('"--apply"'), place.index("app.project.save()"))

    def test_templates_do_not_render_from_the_preset_tree(self):
        daycard = run_tool("presets/road-to-20k/templates/build_daycard.py", "daycard")
        self.assertNotEqual(daycard.returncode, 0)
        self.assertIn("template only", daycard.stderr + daycard.stdout)
        fx = run_tool("presets/road-to-20k/templates/fx/fx17.py", "01")
        self.assertNotEqual(fx.returncode, 0)
        self.assertIn("refusing to render", fx.stderr + fx.stdout)

    def test_asset_gate_stays_open(self):
        proc = run_tool("packaging/assets/check_required_assets.py")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cinepacks-luts", proc.stdout)
        self.assertIn("coolvetica", proc.stdout)
        self.assertIn("sfx-library", proc.stdout)

    def test_public_tree_has_no_private_markers(self):
        banned = ("johnalan", "Desktop Stuff", "/Users/creator", "houston", "gazelle")
        roots = [
            ROOT / "presets/road-to-20k",
            ROOT / "packaging",
        ]
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() in {".prproj", ".pyc"}:
                    continue
                if "tests" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for token in banned:
                    self.assertNotIn(token, text, f"{token} in {path}")


if __name__ == "__main__":
    unittest.main()
