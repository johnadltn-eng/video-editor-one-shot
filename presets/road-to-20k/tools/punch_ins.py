# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless", "numpy"]
# ///
"""Face-centred V1 static/push/punch Motion from premiere/punch-plan.json.
Usage: uv run presets/road-to-20k/tools/punch_ins.py <job> [--reset]
Requires timeline-clips.json, supplied footage and the separately rights-reviewed YuNet model.
Keep hook/card alignment, b-roll and sensitive moments steady; static 1.05-1.10, max 1.12; reapply after rebuild."""
import json, subprocess, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir, REPO

a = sys.argv[1:]
if not a:
    sys.exit(__doc__)
if "--apply" not in a:
    sys.exit("dry-run: pass --apply to write face-points.json and Motion keys. --reset also requires --apply. The YuNet model is rights-gated separately.")
_positional = [arg for arg in a if not arg.startswith("--")]
if not _positional:
    sys.exit(__doc__)
job = job_dir(_positional[0])
clips = json.loads((job / "premiere/timeline-clips.json").read_text())
proj = job / "premiere" / f"{job.name}.prproj"

if "--reset" in a:
    print(es(r"""
(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  var v1 = app.project.activeSequence.videoTracks[0], n = 0;
  for (var i = 0; i < v1.clips.numItems; i++) { var c = v1.clips[i];
    for (var k = 0; k < c.components.numItems; k++) if (c.components[k].displayName === "Motion") { var m = c.components[k];
      for (var p = 0; p < m.properties.numItems; p++) { var pr = m.properties[p];
        if (pr.displayName === "Scale") { if (pr.isTimeVarying()) pr.setTimeVarying(false); pr.setValue(100, 1); }
        if (pr.displayName === "Position") { if (pr.isTimeVarying()) pr.setTimeVarying(false); pr.setValue([0.5, 0.5], 1); } } n++; } }
  app.project.save(); return "OK:reset " + n + " V1 clips";
})()""" % (json.dumps(str(proj)), json.dumps(job.name))))
    sys.exit(0)

plan = json.loads((job / "premiere/punch-plan.json").read_text())
det = cv2.FaceDetectorYN_create(str(REPO / "assets/models/face_detection_yunet_2023mar.onnx"), "", (540, 960), score_threshold=0.6)
faces = {}
for c in clips:
    if str(c["f0"]) not in plan:
        continue
    dur, pts = (c["f1"] - c["f0"]) / 30, []
    for q in (0.2, 0.5, 0.8):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{c['in'] + dur * q:.3f}", "-i", str(job / "raw" / c["clip"]), "-frames:v", "1",
                              "-vf", "scale=540:960", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        if len(raw) < 540 * 960 * 3:
            continue
        f = det.detect(np.frombuffer(raw, np.uint8).reshape(960, 540, 3))[1]
        if f is not None:
            x, y, w, h = f[0][:4]
            pts.append(((x + w / 2) / 540, (y + h * 0.45) / 960))
    faces[str(c["f0"])] = [float(np.median([p[0] for p in pts])), float(np.median([p[1] for p in pts]))] if pts else [0.5, 0.42]
(job / "premiere/face-points.json").write_text(json.dumps(faces, indent=1))
missing = [k for k in plan if k not in faces]
if missing:
    sys.exit(f"punch-plan keys that are not a V1 clip start frame: {missing} (re-run dump_timeline.py)")
rows = [[int(k), *v, faces[k]] for k, v in plan.items()]
print(es(r"""
(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  var ROWS = %s, v1 = app.project.activeSequence.videoTracks[0], out = [];
  function motion(c){ for (var k = 0; k < c.components.numItems; k++) if (c.components[k].displayName === "Motion") return c.components[k]; return null; }
  function prop(m, n){ for (var p = 0; p < m.properties.numItems; p++) if (m.properties[p].displayName === n) return m.properties[p]; return null; }
  function posFor(f, s){ return [f[0] - (f[0] - 0.5) * s, f[1] - (f[1] - 0.5) * s]; }   // keeps face point f fixed under scale s
  for (var r = 0; r < ROWS.length; r++) {
    var row = ROWS[r], f0 = row[0], kind = row[1], face = row[row.length - 1], c = null;
    for (var i = 0; i < v1.clips.numItems; i++) if (Math.round(v1.clips[i].start.seconds * 30) === f0) c = v1.clips[i];
    if (!c) { out.push("MISSING clip @" + f0); continue; }
    var m = motion(c), sc = prop(m, "Scale"), po = prop(m, "Position");
    var src0 = c.inPoint.seconds, tl0 = c.start.seconds, len = c.end.seconds - c.start.seconds;
    function kt(tlFrame){ return src0 + (tlFrame / 30 - tl0); }        // keyframe time = media time
    if (kind === "static") {
      sc.setValue(row[2] * 100, 1); po.setValue(posFor(face, row[2]), 1);
      out.push(f0 + " static " + Math.round(sc.getValue()) + "%%");
    } else {
      sc.setTimeVarying(true); po.setTimeVarying(true);
      var keys = kind === "push" ? [[kt(f0), row[2]], [kt(f0 + len * 30 - 1), row[3]]]
                                 : [[kt(f0), row[2]], [kt(row[4] - 1), row[2]], [kt(row[4] + 4), row[3]]];
      for (var q = 0; q < keys.length; q++) { var t = keys[q][0], s2 = keys[q][1];
        sc.addKey(t); sc.setValueAtKey(t, s2 * 100, 1); po.addKey(t); po.setValueAtKey(t, posFor(face, s2), 1); }
      out.push(f0 + " " + kind + " -> " + Math.round(sc.getValueAtTime(keys[keys.length - 1][0] + 0.05)) + "%%");
    }
  }
  app.project.save();
  return "OK:" + out.join("\n");
})()
""" % (json.dumps(str(proj)), json.dumps(job.name), json.dumps(rows))))
