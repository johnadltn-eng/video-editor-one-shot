#!/usr/bin/env python3
"""Road to 20K: lay b-roll, stills and overlays on the job's sequence from premiere/place.json.

  python3 presets/road-to-20k/tools/place.py <job>

place.json = {"rows": [[track, "relative/path", start_frame, n_frames, src_in_seconds_or_null], ...]}
  track 0 = V1 (only AFTER the A-roll, e.g. a still), 1 = V2 b-roll, 2 = V3 captions, 3 = V4 title/pops, 4 = V5 timestamps
Idempotent per track: clears V2-V5 (and any V1 item placed after the A-roll) before laying the rows.
B-roll is muted: overwriteClip lays a clip's own audio on A2+, and only THAT linked audio is removed
(anything else on A2+, e.g. a music bed John added by hand, is left alone). Footage from raw/ or broll/ gets
its frame rate pinned to 30 like the A-roll; graphics are rendered at 30 already.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir, ACTIVATE

job = job_dir(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
plan = json.loads((job / "premiere" / "place.json").read_text())
rows = [[r[0], str((job / r[1]).resolve()), r[2], r[3], r[4]] for r in plan["rows"]]
for r in rows:
    if not Path(r[1]).exists(): sys.exit(f"missing: {r[1]}")
proj = job / "premiere" / f"{job.name}.prproj"
print(es(r"""
(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  var ROWS = %s, F = 30, N = 1e-4, seq = app.project.activeSequence, root = app.project.rootItem;
  function find(bin, p){ for (var i = 0; i < bin.children.numItems; i++) { var c = bin.children[i];
    if (c.type === ProjectItemType.BIN) { var x = find(c, p); if (x) return x; } else if (c.getMediaPath && c.getMediaPath() === p) return c; } return null; }
  while (seq.videoTracks.numTracks < 5) { app.enableQE(); qe.project.getActiveSequence().addTracks(1, seq.videoTracks.numTracks, 0); }
  var v1 = seq.videoTracks[0], aEnd = 0;
  for (var c = 0; c < v1.clips.numItems; c++) { var x = v1.clips[c], p = x.projectItem ? x.projectItem.getMediaPath() : "";
    if (p.indexOf("/raw/") >= 0 && x.end.seconds > aEnd) aEnd = x.end.seconds; }
  for (var t = 1; t < 5; t++) for (var c = seq.videoTracks[t].clips.numItems - 1; c >= 0; c--) seq.videoTracks[t].clips[c].remove(false, false);
  for (var c = v1.clips.numItems - 1; c >= 0; c--) if (v1.clips[c].start.seconds >= aEnd - 0.01) v1.clips[c].remove(false, false);
  var placed = {}, out = [];
  for (var r = 0; r < ROWS.length; r++) {
    var row = ROWS[r], tr = seq.videoTracks[row[0]], path = row[1], s = row[2] / F, e2 = (row[2] + row[3]) / F;
    var item = find(root, path); if (!item) { app.project.importFiles([path], true, root, false); item = find(root, path); }
    if (!item) return "ERROR: import failed " + path;
    if (path.indexOf("/raw/") >= 0 || path.indexOf("/broll/") >= 0) { if (!/\.(png|jpe?g)$/i.test(path)) item.setOverrideFrameRate(30); placed[path] = 1; }
    if (row[4] !== null) { item.setInPoint(row[4] + N, 4); item.setOutPoint(row[4] + row[3] / F + N, 4); }
    tr.overwriteClip(item, s + N);
    if (row[4] !== null) { item.clearInPoint(4); item.clearOutPoint(4); }
    var clip = null; for (var i = 0; i < tr.clips.numItems; i++) if (Math.abs(tr.clips[i].start.seconds - s) < 0.02) clip = tr.clips[i];
    if (!clip) return "ERROR: did not land " + path + " at frame " + row[2];
    var te = new Time(); te.seconds = e2 + N; clip.end = te;
    out.push("V" + (row[0] + 1) + " " + clip.name + " " + Math.round(clip.start.seconds * F) + "->" + Math.round(clip.end.seconds * F));
  }
  var gone = 0;
  for (var t = 1; t < seq.audioTracks.numTracks; t++) for (var c = seq.audioTracks[t].clips.numItems - 1; c >= 0; c--) {
    var a = seq.audioTracks[t].clips[c], p = a.projectItem ? a.projectItem.getMediaPath() : "";
    if (placed[p]) { a.remove(false, false); gone++; } }
  app.project.save();
  return "OK:" + out.join("\n") + "\nb-roll linked audio removed from A2+: " + gone;
})()""" % (json.dumps(str(proj)), json.dumps(job.name), json.dumps(rows))))
