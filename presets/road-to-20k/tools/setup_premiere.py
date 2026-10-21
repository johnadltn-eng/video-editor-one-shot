#!/usr/bin/env python3
"""Road to 20K: create the Premiere project + sequence for a Day N job and import its raw clips.

  python3 presets/road-to-20k/tools/setup_premiere.py <job>

- project  projects/<job>/premiere/<job>.prproj   (created if missing; an existing one is reused)
- sequence <job>, 1080x1920, EXACT 30 fps (ticks 8467200000), all tracks emptied
- every file in raw/ imported with its frame rate pinned to the nominal rate Premiere should use:
  iPhone 29.998 -> 30 · 119.95 -> 120 (slo-mo files play real time) · 23.998 -> 24 · 59.9x -> 60 · 29.97 -> 30000/1001
  (Premiere reads iPhone footage as 29.9987 and floors in-points a frame early unless overridden)
Prints the per-clip read/override rates. Idempotent: re-running reuses the project, re-imports nothing twice.
"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir, REPO, BRIDGE

job = job_dir(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
name = job.name
proj = job / "premiere" / f"{name}.prproj"
(job / "premiere").mkdir(exist_ok=True)
if not proj.exists():
    subprocess.run(["node", str(BRIDGE), "create_project", json.dumps({"name": name, "location": str(job / "premiere")})],
                   capture_output=True, text=True, cwd=REPO)
    if not proj.exists():
        sys.exit(f"create_project did not write {proj}")
raws = sorted(str(p) for p in (job / "raw").iterdir() if p.suffix.lower() in (".mov", ".mp4", ".m4v"))
print(es(r"""
(function(){
  var P = %s, NAME = %s, RAWS = %s;
  if (app.project.path !== P) app.openDocument(P);
  if (app.project.path !== P) return "ERROR: could not open " + P;
  var root = app.project.rootItem;
  function byPath(b, p){ for (var i = 0; i < b.children.numItems; i++) { var c = b.children[i];
    if (c.type === ProjectItemType.BIN) { var x = byPath(c, p); if (x) return x; } else if (c.getMediaPath && c.getMediaPath() === p) return c; } return null; }
  var todo = []; for (var i = 0; i < RAWS.length; i++) if (!byPath(root, RAWS[i])) todo.push(RAWS[i]);
  if (todo.length) app.project.importFiles(todo, true, root, false);
  function nominal(r){ var c = [24, 25, 30, 48, 50, 60, 100, 120, 240];
    if (Math.abs(r - 29.97) < 0.005) return 30000/1001; if (Math.abs(r - 23.976) < 0.003) return 24000/1001; if (Math.abs(r - 59.94) < 0.005) return 60000/1001;
    var best = c[0]; for (var i = 0; i < c.length; i++) if (Math.abs(c[i] - r) < Math.abs(best - r)) best = c[i]; return best; }
  var o = [], first = null;
  for (var i = 0; i < RAWS.length; i++) { var it = byPath(root, RAWS[i]); if (!it) { o.push("MISSING " + RAWS[i]); continue; }
    if (!first) first = it; var r = it.getFootageInterpretation().frameRate, n = nominal(r); it.setOverrideFrameRate(n);
    o.push(it.name + " read " + r.toFixed(4) + " -> " + (Math.round(n * 1000) / 1000)); }
  var seq = null; for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name === NAME) seq = app.project.sequences[i];
  if (!seq) { seq = app.project.createNewSequenceFromClips(NAME, [first], root); }
  app.project.activeSequence = seq;
  for (var t = 0; t < seq.videoTracks.numTracks; t++) { var vt = seq.videoTracks[t]; for (var k = vt.clips.numItems - 1; k >= 0; k--) vt.clips[k].remove(false, false); }
  for (var t = 0; t < seq.audioTracks.numTracks; t++) { var at = seq.audioTracks[t]; for (var k = at.clips.numItems - 1; k >= 0; k--) at.clips[k].remove(false, false); }
  var s = seq.getSettings(); var tt = new Time(); tt.ticks = "8467200000"; s.videoFrameRate = tt; seq.setSettings(s); s = seq.getSettings();
  if (s.videoFrameWidth !== 1080 || s.videoFrameHeight !== 1920) o.push("WARNING sequence is " + s.videoFrameWidth + "x" + s.videoFrameHeight + " (expected 1080x1920: check the first clip's rotation)");
  app.project.save();
  return "OK:seq " + NAME + " " + s.videoFrameWidth + "x" + s.videoFrameHeight + " @ " + (1 / s.videoFrameRate.seconds).toFixed(3) + " fps\n" + o.join("\n");
})()""" % (json.dumps(str(proj)), json.dumps(name), json.dumps(raws))))
