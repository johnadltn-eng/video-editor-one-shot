#!/usr/bin/env python3
"""Per-source A1 voice level matching from kept speech.
Usage: python3 presets/road-to-20k/tools/level_match.py <job> --auto [--dry] [--target -15]
Manual override: --set sample-a.mov=-9.5
Apply audio-polish --apply --gain 0 --limit -2 FIRST; this writes per-source Amplify afterwards. Gains clamp to [-12,+15] dB."""
import json, re, subprocess, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir

a = sys.argv[1:]
if not a:
    sys.exit(__doc__)
_positional = [arg for arg in a if not arg.startswith("--")]
if not _positional:
    sys.exit(__doc__)
job = job_dir(_positional[0])
target = float(a[a.index("--target") + 1]) if "--target" in a else -15.0
levels_p = job / "premiere" / "levels.json"
gains = json.loads(levels_p.read_text()) if levels_p.exists() else {}

if "--auto" in a:
    segs = json.loads((job / "transcript" / "cuts.json").read_text())["segments"]
    by = collections.defaultdict(list)
    for s in segs:
        by[s["clip"]].append(s)
    for c, ss in by.items():
        args = ["ffmpeg", "-nostats", "-v", "info"]
        for s in ss:
            args += ["-ss", str(s["start"]), "-to", str(s["end"]), "-i", str(job / "raw" / c)]
        fc = "".join(f"[{i}:a]" for i in range(len(ss))) + f"concat=n={len(ss)}:v=0:a=1,ebur128=peak=true"
        r = subprocess.run(args + ["-filter_complex", fc, "-f", "null", "-"], capture_output=True, text=True).stderr
        lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
        peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
        g = round(max(-12.0, min(15.0, target - lufs)) * 2) / 2
        gains[c] = g
        print(f"{c:22s} kept {sum(s['end'] - s['start'] for s in ss):5.1f}s  {lufs:6.1f} LUFS  peak {peak:5.1f}  -> {g:+.1f} dB")
for kv in [a[i + 1] for i, x in enumerate(a) if x == "--set"]:
    k, v = kv.split("=")
    gains[k] = float(v)
if "--apply" not in a or "--dry" in a:
    print("dry-run: gains not written and the timeline was not changed. Pass --apply after audio-polish.")
    sys.exit(0)
levels_p.write_text(json.dumps(gains, indent=1))
print(es(r"""
(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  var G = %s, out = [], t = app.project.activeSequence.audioTracks[0];
  for (var i = 0; i < t.clips.numItems; i++) {
    var c = t.clips[i], g = G[c.projectItem.name]; if (g === undefined) { out.push("skip " + c.projectItem.name); continue; }
    var amp = null; for (var k = 0; k < c.components.numItems; k++) if (c.components[k].displayName === "Amplify") amp = c.components[k];
    if (!amp) return "ERROR: no Amplify on A1 clip " + i + " (run audio-polish.py --apply first)";
    var v = (g + 96) / 144, n = 0;
    for (var p = 0; p < amp.properties.numItems; p++) { var pr = amp.properties[p];
      if (pr.displayName === "Left" || pr.displayName === "Right") { pr.setValue(v, 1); if (Math.abs(pr.getValue() - v) > 1e-4) return "ERROR: readback clip " + i; n++; } }
    out.push(i + " " + c.projectItem.name + " " + (g >= 0 ? "+" : "") + g + " dB");
  }
  app.project.save();
  return "OK:" + out.join("\n");
})()
""" % (json.dumps(str(job / "premiere" / f"{job.name}.prproj")), json.dumps(job.name), json.dumps(gains))))
