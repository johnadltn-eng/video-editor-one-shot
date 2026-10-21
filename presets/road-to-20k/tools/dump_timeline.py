#!/usr/bin/env python3
"""Road to 20K: write premiere/timeline-clips.json = every A-roll clip on V1 as it sits on the timeline right now.

  python3 presets/road-to-20k/tools/dump_timeline.py <job>

One row per V1 clip from raw/: {clip, f0, f1, in} (timeline frames @30, source in-point in seconds). The overlay
builder maps every caption word by its SOURCE time to whichever timeline clip shows that moment, so captions follow
John's hand edits of any kind (ripple deletes, trims, splits, reorders) and Premiere's 1-2 frame rounding of 120/24 fps
clips. Re-run after ANY timeline change, then re-render captions. Also lists EDL segments no longer on the timeline.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir, ACTIVATE

job = job_dir(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
proj = job / "premiere" / f"{job.name}.prproj"
raw = es(r"""
(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  var v = app.project.activeSequence.videoTracks[0], o = [];
  for (var k = 0; k < v.clips.numItems; k++) { var x = v.clips[k];
    o.push(x.name + "|" + Math.round(x.start.seconds * 30) + "|" + Math.round(x.end.seconds * 30) + "|" + x.inPoint.seconds.toFixed(4) + "|" + (x.projectItem ? x.projectItem.getMediaPath() : "")); }
  return "OK:" + o.join("\n"); })()""" % (json.dumps(str(proj)), json.dumps(job.name)))
tl = []
for line in raw.splitlines():
    n, f0, f1, i, path = line.split("|")
    if "/raw/" not in path:      # graphics / stills on V1 (slates, end-card stills) are not A-roll
        continue
    tl.append(dict(clip=n, f0=int(f0), f1=int(f1), **{"in": float(i)}))
tl.sort(key=lambda c: c["f0"])
(job / "premiere" / "timeline-clips.json").write_text(json.dumps(tl, indent=0))
print(f"{len(tl)} A-roll clips on V1, ends at frame {tl[-1]['f1']} ({tl[-1]['f1'] / 30:.3f}s) -> premiere/timeline-clips.json")
segs = json.loads((job / "transcript" / "cuts.json").read_text())["segments"]
for s in segs:   # report EDL lines whose footage no longer appears anywhere on V1
    mid = (s["start"] + s["end"]) / 2
    if not any(c["clip"] == s["clip"] and c["in"] - 0.02 <= mid < c["in"] + (c["f1"] - c["f0"]) / 30 for c in tl):
        print("  not on the timeline:", s.get("transcript", s["clip"]))
