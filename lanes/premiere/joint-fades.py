#!/usr/bin/env python3
"""joint-fades.py: pipeline step 3 on the Premiere lane, a short audio crossfade on every A1 joint.

  uv run lanes/premiere/joint-fades.py projects/<job> --apply       # 2-frame Constant Gain on every bare A1 joint, read back, save
  uv run lanes/premiere/joint-fades.py projects/<job> --verify      # exit 1 if any A1 joint has no transition
  uv run lanes/premiere/joint-fades.py projects/<job> --apply --frames 3 --type "Constant Power"

House standard (John, 2026-10-16, day-005-road-to-20k): every cut on the voice track gets a
small Constant Gain, 00:00:00:02, centred on the joint. It takes the edge off jump cuts
("sounds much better") without the long-fade problem: a centred fade plays half its length of
the material past the cut, so at 9 frames a tight cut fades a removed word back in ("30",
"like", "that"); at 2 frames that is one frame per side, which holds no separate word.

  - a joint = two A1 clips butted together (end == next start within 1 ms); gaps are left alone
  - a joint that already carries ANY transition is skipped: hand-placed fades (other types,
    other lengths) are the editor's and are never replaced
  - QE addTransition(t, true, frames, "0", 0.5, false, true) on the clip that STARTS at the
    joint lands centred on that joint (measured 2026-10-16: the flag means "at start" here,
    the opposite of what the vendored add_transition_to_clip assumes)
  - run AFTER audio-polish.py; a timeline rebuild (re-replay) drops transitions: run --apply again
"""
import json, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit(f"{' '.join(cmd[:3])} failed:\n{r.stderr or r.stdout}")
    return r.stdout


def es(script):
    out = sh('node', str(BRIDGE), 'execute_extendscript', json.dumps({'script': script}))
    lines = out.splitlines(); j = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i][:1] in '{["':
            try: j = json.loads('\n'.join(lines[i:])); break
            except json.JSONDecodeError: continue
    if j is None: sys.exit(f'bridge returned non-JSON:\n{out[-800:]}')
    if isinstance(j, dict) and j.get('success') is False: sys.exit(f"bridge error: {j.get('error')}")
    d = j.get('data', j) if isinstance(j, dict) else j
    if isinstance(d, dict): d = d.get('result', d)
    return d if isinstance(d, str) else json.dumps(d)


def run(apply, frames, ttype):
    r = es(r"""
(function(){
  var seq = app.project.activeSequence; if (!seq) return "ERROR: no active sequence";
  var APPLY = %s, FR = %d, TYPE = %s;
  var a1 = seq.audioTracks[0], out = {joints: 0, had: 0, added: 0, bad: [], gaps: 0};
  var fps = 1 / seq.getSettings().videoFrameRate.seconds, half = FR / fps / 2 + 0.02;
  function near(j){ for (var i = 0; i < a1.transitions.numItems; i++) { var x = a1.transitions[i];
    if (x.start.seconds < j + 0.02 && x.end.seconds > j - 0.02) return x; } return null; }
  var qtr = null, tr = null;
  if (APPLY) { app.enableQE(); qtr = qe.project.getActiveSequence().getAudioTrackAt(0);
    tr = qe.project.getAudioTransitionByName(TYPE); if (!tr) return "ERROR: no audio transition named " + TYPE; }
  function qAt(t){ for (var q = 0; q < qtr.numItems; q++) { var it = qtr.getItemAt(q);
    if (it.type === "Clip" && Math.abs(it.start.secs - t) < 0.002) return it; } return null; }
  var J = [];
  for (var i = 0; i + 1 < a1.clips.numItems; i++) {
    var e = a1.clips[i].end.seconds, s = a1.clips[i + 1].start.seconds;
    if (Math.abs(e - s) < 0.001) J.push(s); else out.gaps++;
  }
  out.joints = J.length;
  for (var k = 0; k < J.length; k++) {
    var j = J[k];
    if (near(j)) { out.had++; continue; }
    if (!APPLY) { out.bad.push(j.toFixed(3) + ": no transition"); continue; }
    var it = qAt(j); if (!it) { out.bad.push(j.toFixed(3) + ": no QE item"); continue; }
    it.addTransition(tr, true, String(FR), "0", 0.5, false, true);
    var t = near(j);
    if (!t || t.name !== TYPE || Math.abs((t.start.seconds + t.end.seconds) / 2 - j) > half)
      out.bad.push(j.toFixed(3) + ": not verified (" + (t ? t.name + " " + t.start.seconds.toFixed(3) + "-" + t.end.seconds.toFixed(3) : "none") + ")");
    else out.added++;
  }
  if (APPLY && !out.bad.length) app.project.save();
  return JSON.stringify(out);
})()""" % ('true' if apply else 'false', frames, json.dumps(ttype)))
    if str(r).startswith('ERROR'): sys.exit(r)
    return json.loads(r)


def main():
    a = sys.argv[1:]
    if len(a) < 2 or not ({'--apply', '--verify'} & set(a)): sys.exit(__doc__)
    frames = int(a[a.index('--frames') + 1]) if '--frames' in a else 2
    ttype = a[a.index('--type') + 1] if '--type' in a else 'Constant Gain'
    apply = '--apply' in a
    got = run(apply, frames, ttype)
    print(f"A1 joints {got['joints']} · already faded {got['had']} · added {got['added']} × {frames}-frame {ttype}"
          f" · gaps left alone {got['gaps']}")
    for b in got['bad']: print('✗ ' + b)
    if got['bad']: sys.exit(1)
    if apply: print('saved')


if __name__ == '__main__':
    main()
