#!/usr/bin/env python3
"""Inspect all video/audio tracks before any follow-up after manual editing.
Usage: python3 presets/road-to-20k/tools/tracks.py <job> [--save]
Prints clip start/end frames, in/out and disabled state; --save writes a timestamped inspection.
Bridge activation can change active project/sequence despite otherwise read-only inspection."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir

job = job_dir(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
res = es(r"""
(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  var seq = app.project.activeSequence, out = [];
  function dump(tr, lab){ for (var k = 0; k < tr.clips.numItems; k++) { var c = tr.clips[k];
    out.push(lab + "\t" + c.name + "\tf" + Math.round(c.start.seconds*30) + "-" + Math.round(c.end.seconds*30) +
             "\tin " + c.inPoint.seconds.toFixed(3) + "\tout " + c.outPoint.seconds.toFixed(3) + (c.disabled ? "\tDISABLED" : "")); } }
  for (var t = 0; t < seq.videoTracks.numTracks; t++) dump(seq.videoTracks[t], "V" + (t+1));
  for (var t = 0; t < seq.audioTracks.numTracks; t++) dump(seq.audioTracks[t], "A" + (t+1));
  return "OK:" + out.join("\n");
})()
""" % (json.dumps(str(job / "premiere" / f"{job.name}.prproj")), json.dumps(job.name)))
print(res)
if "--save" in sys.argv:
    p = job / "premiere" / f"tracks-{time.strftime('%Y%m%d-%H%M%S')}.txt"
    p.write_text(res + "\n")
    print("->", p.relative_to(job))
