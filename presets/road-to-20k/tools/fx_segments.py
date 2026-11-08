#!/usr/bin/env python3
"""Frame-exact effect segment and optional person-matte preparation.
Usage: python3 presets/road-to-20k/tools/fx_segments.py <job> effect=0-90[:nomatte] ...
Renders flat cut if absent; writes 1080x1920 exact-30fps segments and hyperframes@0.8.16 person mattes.
No models, media or assets accompany this review copy."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import job_dir, REPO

a = sys.argv[1:]
if "--apply" not in a:
    sys.exit("dry-run: pass --apply to render frame-exact segments into the job fx/ folder. Job raw files are not moved.")
a = [x for x in a if x != "--apply"]
if len(a) < 2:
    sys.exit(__doc__)
job = job_dir(a[0])
base = job / "outputs" / f"{job.name}.mp4"
if not base.exists():
    print("rendering the flat face cut (RENDER=1 splice.sh)…")
    subprocess.run(["bash", str(REPO / ".claude/skills/rough-cut/scripts/splice.sh"), str(job)], check=True,
                   env={**__import__("os").environ, "AMPLIFY_DB": "0", "RENDER": "1"}, cwd=REPO, stdout=subprocess.DEVNULL)
fx = job / "fx"
for d in ("src", "build", "outputs", "assets", "check"):
    (fx / d).mkdir(parents=True, exist_ok=True)
for spec in a[1:]:
    name, rng = spec.split("=")
    matte = not rng.endswith(":nomatte")
    f0, f1 = (int(x) for x in rng.replace(":nomatte", "").split("-"))
    n, d = f1 - f0, (f1 - f0) / 30
    src = fx / "src" / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{f0 / 30:.6f}", "-i", str(base), "-frames:v", str(n), "-vf", "fps=30,scale=1080:1920",
                    "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-af", f"atrim=0:{d:.6f}", str(src)], check=True)
    got = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries", "stream=nb_read_frames",
                          "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip()
    line = f"{name:12s} f{f0}-{f1}  {got}/{n} frames"
    if matte:
        cut = fx / "build" / f"{name}-cutout.mov"
        subprocess.run(["npx", "-y", "hyperframes@0.8.16", "remove-background", str(src), "-o", str(cut)], check=True, cwd=REPO,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        line += "  matte ok" if cut.exists() else "  MATTE FAILED"
    print(line)
