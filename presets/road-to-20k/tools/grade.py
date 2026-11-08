#!/usr/bin/env python3
"""Per-footage house grade compatibility utility for Premiere 25.6.2.
Usage: python3 presets/road-to-20k/tools/grade.py <job> --apply
Adds Lumetri to V1/V2, backs up once, closes the project, replays the captured look, checks hash references, then reopens.
Default is dry-run. --apply is required before any save, close, or project write.
CAUTION: closeDocument has dropped the bridge. Not certified for unattended use or for Premiere 25.6.2.
Captured look rights and the 26.3.2 parameter format remain unresolved."""
import importlib.util, io, contextlib, json, re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir, REPO

if "--apply" not in sys.argv:
    sys.exit(
        "dry-run: refusing to save, close, or write a project.\n"
        "Pass --apply to back up the job .prproj, add Lumetri on V1/V2, close that project, "
        "write the captured look, and reopen it.\n"
        "closeDocument can drop the bridge. This is not a Premiere 25.6.2 certification. "
        "The captured LUT is not cleared for redistribution."
    )
_positional = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
job = job_dir(_positional[0] if _positional else sys.exit(__doc__))
P = job / "premiere" / f"{job.name}.prproj"
bak = job / "premiere" / f"{job.name}.pre-grade.prproj"
if not bak.exists():
    shutil.copy(P, bak)


print(es(r"""
(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  app.enableQE();
  var seq = app.project.activeSequence, qs = qe.project.getActiveSequence(), eff = qe.project.getVideoEffectByName("Lumetri Color");
  if (!eff) return "ERROR: no Lumetri Color";
  var added = 0, total = 0, bad = [];
  for (var t = 0; t < 2 && t < seq.videoTracks.numTracks; t++) {
    var qt = qs.getVideoTrackAt(t), n = -1;
    for (var i = 0; i < qt.numItems; i++) { var it = qt.getItemAt(i); if (!it || it.type !== "Clip") continue; n++;
      var c = seq.videoTracks[t].clips[n], has = false;
      for (var k = 0; k < c.components.numItems; k++) if (c.components[k].displayName === "Lumetri Color") has = true;
      if (!has) { it.addVideoEffect(eff); added++; } }
    for (var i = 0; i < seq.videoTracks[t].clips.numItems; i++) { var c = seq.videoTracks[t].clips[i], m = 0; total++;
      for (var k = 0; k < c.components.numItems; k++) if (c.components[k].displayName === "Lumetri Color") m++;
      if (m !== 1) bad.push("V" + (t + 1) + " " + c.name + " has " + m); }
  }
  app.project.save();
  return "OK:Lumetri added " + added + " · footage clips " + total + (bad.length ? "\n" + bad.join("\n") : " · each has exactly one");
})()
""" % (json.dumps(str(P)), json.dumps(job.name))))


print(es(r"""
(function(){ var P = %s;
  for (var i = 0; i < app.projects.numProjects; i++) { var p = app.projects[i];
    if (p.path === P) { p.save(); p.closeDocument(1, 0); return "OK:closed " + P; } }
  return "OK:not open";
})()
""" % json.dumps(str(P))))


spec = importlib.util.spec_from_file_location("gradelut", REPO / "lanes/premiere/grade-lut.py")
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)


def component_pfpd(xml, which=0):
    b = G.lumetri_component(xml, which).group(0)
    m = (re.search(r'<PremiereFilterPrivateData[^>]*>.*?</PremiereFilterPrivateData>', b, re.S) or
         re.search(r'<PremiereFilterPrivateData[^>]*?/>', b, re.S))
    return m.group(0)


G.component_pfpd = component_pfpd
params = G.resolve_params(G.DEFAULT_LUT)
n = len([m for m in re.finditer(r'<VideoFilterComponent ObjectID="(\d+)"[^>]*>(.*?)</VideoFilterComponent>', G.load(P), re.S)
         if 'AE.ADBE Lumetri' in m.group(2)])
for w in range(n):
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        G.cmd_apply(str(P), params, w)
x = G.load(P)
dangling = set(re.findall(r'BinaryHash="([^"]+)"[^>]*?/>', x)) - set(re.findall(r'BinaryHash="([^"]+)"[^>/]*>', x))
print(f"look ({G.DEFAULT_LUT}) written into {n} Lumetri instances · dangling binary pointers: {len(dangling)}")
if dangling:
    sys.exit("DANGLING binary pointers — restore " + str(bak))


print(es(r"""(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e; return "OK:reopened " + app.project.activeSequence.name; })()"""
         % (json.dumps(str(P)), json.dumps(job.name))))
