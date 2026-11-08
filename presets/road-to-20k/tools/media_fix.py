#!/usr/bin/env python3
"""Pre-edit media utility; transcript aliases follow the derived filename.
Usage: python3 presets/road-to-20k/tools/media_fix.py <job> blur|cfr <clip> --apply [--move-original] [--alias] [--y 1480]
Blur lower frame with a 140px feather, or conform VFR to exact 30fps.
Default does not encode, move, or edit words.json. --apply writes a derived file beside the clip.
--move-original also moves that job-local raw file into raw-unblurred/ or raw-vfr/. Files outside the job are never moved.
--alias appends a words.json clip alias. Library footage outside the job is not a source."""
import json, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import job_dir

a = sys.argv[1:]
if "--apply" not in a:
    sys.exit(
        "dry-run: refusing to encode, move an original, or edit words.json.\n"
        "Pass --apply to write the derived file inside the job. "
        "Pass --move-original as well to move only that job-local raw file aside. "
        "Pass --alias to append a words.json clip alias."
    )
if len(a) < 3:
    sys.exit(__doc__)
positional = [arg for arg in a if arg not in {"--apply", "--move-original", "--alias"} and not arg.startswith("--y")]
# --y consumes the following value; drop it from positionals if present.
if "--y" in a:
    y_value = a[a.index("--y") + 1]
    positional = [arg for arg in positional if arg != y_value]
if len(positional) < 3:
    sys.exit(__doc__)
job, mode, name = job_dir(positional[0]), positional[1], positional[2]
if name != Path(name).name or name in {".", ".."}:
    sys.exit("clip must be a file name inside the job raw/ folder")
src = (job / "raw" / name).resolve()
raw_root = (job / "raw").resolve()
if raw_root != src.parent:
    sys.exit("refusing to read a file outside the job raw/ folder")
if not src.exists():
    sys.exit(f"missing {src}")
stem = src.stem
if mode == "blur":
    y = int(a[a.index("--y") + 1]) if "--y" in a else 1480
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                               capture_output=True, text=True).stdout)
    out, keep = job / "raw" / f"{stem}-blur.mov", job / "raw-unblurred"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-f", "lavfi", "-i",
                    f"color=black:s=1080x1920:r=30,format=gray,geq=lum='clip((Y-{y})/140\\,0\\,1)*255'",
                    "-filter_complex", f"[0:v]split[a][b];[b]boxblur=30:3[bl];[1:v]trim=duration={dur + 1}[m];[bl][m]alphamerge[blm];[a][blm]overlay=0:0:shortest=1",
                    "-fps_mode", "passthrough", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-map", "0:a:0", "-c:a", "copy", "-map_metadata", "0", "-movflags", "use_metadata_tags", str(out)], check=True)
elif mode == "cfr":
    out, keep = job / "raw" / f"{stem}-cfr.mov", job / "raw-vfr"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0", "-vf", "fps=30",
                    "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-map_metadata", "0", "-movflags", "use_metadata_tags", str(out)], check=True)
else:
    sys.exit(__doc__)
if "--move-original" in a:
    keep.mkdir(exist_ok=True)
    dest = (keep / name).resolve()
    if dest.parent != keep.resolve():
        sys.exit("refusing to move the original outside the job")
    shutil.move(str(src), str(dest))
    moved = f"original -> {keep.name}/{name}"
else:
    moved = "original left in raw/"
if "--alias" in a:
    wp = job / "transcript" / "words.json"
    if wp.exists():
        d = json.loads(wp.read_text())
        if not any(c["clip"] == out.name for c in d["clips"]):
            for c in list(d["clips"]):
                if c["clip"] == name:
                    d["clips"].append(dict(c, clip=out.name))
            wp.write_text(json.dumps(d, indent=1))
    alias = "words.json alias updated"
else:
    alias = "words.json not edited"
print(f"wrote raw/{out.name} ({moved}); {alias}. Use '{out.name}' in author_edl.py, re-splice.")
