#!/usr/bin/env python3
"""place-graphics.py: owns hf-graphics/placement.json and the Premiere graphics tracks (V3/V4).

  uv run lanes/premiere/place-graphics.py projects/<job> --plan [--write]   # derive rows from the plan + renders; --write saves
  uv run lanes/premiere/place-graphics.py projects/<job> --verify           # timeline readback vs placement.json (exit 1 on drift)
  uv run lanes/premiere/place-graphics.py projects/<job> --apply            # place every row not yet on the timeline; swap stale versions
  uv run lanes/premiere/place-graphics.py projects/<job> --remove g4        # take a graphic off the timeline (before a re-render swap)
  uv run lanes/premiere/place-graphics.py projects/<job> --sync-plan        # write placed start/end back into graphics-plan.json

Why (2026-09-02): eight hand-written ExtendScript batches each needed a matching hand edit to
placement.json and two post-hoc plan reconciliations; the "plan fidelity" reviewer then raised
frame-snap drift as defects. One owner for the rows, one readback that is the truth, and a
`--sync-plan` so the plan and the timeline never disagree by a rounding.

Rows: {"id", "file", "start", "end", "kind": "text"|"full"|"overlay", "track": 2|3}
  text     the text-animation builder's render; start/end from its <id>.meta.json (the builder owns timing)
  full     a punch-cut mp4; start/end from the plan cell (end == a V1 cut, validate-plan.py enforces it)
  overlay  an alpha mov; start from the plan cell, end = start + the render's duration
  track    2 = V3 (graphics), 3 = V4 (accents), a row overlapping an earlier V3 row goes to V4
The newest VERSION of a render wins (g4-alpha-d.mov over g4-alpha-c.mov): re-renders never overwrite.

Premiere is driven through lanes/premiere/premiere-bridge.mjs (headless, bridge panel running). Placement
is DOM overwriteClip at start + 1e-4 (the same nudge as the EDL replay: a double a hair below the
frame tick gets FLOORED into the previous frame), then the clip's end is pinned. Removal is DOM
TrackItem.remove(false, false) with a QE fallback. Every write is read back before it is believed.
"""
import json, os, re, subprocess, sys, glob
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

BRIDGE = Path(__file__).resolve().parent / 'premiere-bridge.mjs'
NUDGE = 1e-4


def sh(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"{' '.join(cmd[:3])} failed:\n{r.stderr or r.stdout}")
    return r.stdout


def es(script):
    """Run ExtendScript through the bridge; return the string result."""
    out = sh('node', str(BRIDGE), 'execute_extendscript', json.dumps({'script': script}))
    try:
        j = json.loads(out)
    except json.JSONDecodeError:
        sys.exit(f'bridge returned non-JSON:\n{out[:800]}')
    if isinstance(j, dict) and j.get('success') is False:
        sys.exit(f"bridge error: {j.get('error')}")
    d = j.get('data', j) if isinstance(j, dict) else j
    if isinstance(d, dict): d = d.get('result', d)
    return d if isinstance(d, str) else json.dumps(d)


def probe_dur(path):
    return float(sh('ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration',
                    '-of', 'csv=p=0', path).strip() or 0)


def probe_fps(path):
    r = sh('ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', path)
    n, _, d = r.strip().split('\n')[0].strip(',').partition('/')
    return float(n) / float(d or 1)


def version_key(p):
    m = re.search(r'-([a-z])\.(mov|mp4)$', p)
    return (m.group(1) if m else '', p)


def newest(pattern):
    c = sorted(glob.glob(pattern), key=version_key)
    return c[-1] if c else None


class Placer:
    def __init__(self, job):
        self.job = Path(job).resolve()
        self.hf = self.job / 'hf-graphics'
        self.pj = self.hf / 'placement.json'
        self.rows = json.load(open(self.pj)) if self.pj.exists() else []
        for r in self.rows:
            if r.get('kind') == 'alpha': r['kind'] = 'overlay'     # older rows named the format, not the role
        self.plan_p = self.job / 'graphics-plan.json'
        self.plan = json.load(open(self.plan_p))
        self.cells = [b for b in self.plan['beats'] if b.get('graphic')]
        self.fps = None

    def F(self):
        if self.fps is None:
            f = next((r['file'] for r in self.rows if os.path.exists(r['file'])), None)
            self.fps = probe_fps(f) if f else 30000 / 1001
        return 1.0 / self.fps

    # ── rows from the plan ──────────────────────────────────────────────────
    def derive(self):
        have = {r['id']: r for r in self.rows}
        out, changes = [], []
        for c in self.cells:
            gid, kind = c['id'], c.get('kind')
            row = dict(have.get(gid, {}))
            if kind == 'text-animation':
                meta = self.hf / 'text-animation' / 'compositions' / f'{gid}.meta.json'
                f = newest(str(self.hf / 'text-animation' / 'renders' / f'{gid}-alpha*.mov'))
                if not meta.exists() or not f:
                    changes.append(f'{gid}: text animation not built/rendered yet'); continue
                m = json.load(open(meta))
                new = dict(id=gid, file=f, start=round(m['place'], 4), end=round(m['place'] + m['duration'], 4), kind='text')
            elif kind in ('punch-cut', 'full-screen', 'scene') or c.get('bg'):
                f = newest(str(self.hf / 'gfx' / 'renders' / f'{gid}*.mp4'))
                if not f: changes.append(f'{gid}: no full-screen render yet'); continue
                new = dict(id=gid, file=f, start=round(float(c['start']), 4), end=round(float(c['end']), 4), kind='full')
            else:
                f = newest(str(self.hf / 'gfx' / 'renders' / f'{gid}-alpha*.mov'))
                if not f: changes.append(f'{gid}: no overlay render yet'); continue
                new = dict(id=gid, file=f, start=round(float(c['start']), 4),
                           end=round(float(c['start']) + probe_dur(f), 4), kind='overlay')
            new['track'] = row.get('track', 2)
            # a row already placed within 1.5 frames of the derived time keeps its placed value: a
            # sub-frame rounding (or a deliberate one-frame nudge to close a hole) is not a change
            for k in ('start', 'end'):
                if k in row and abs(float(row[k]) - new[k]) <= 1.5 * self.F():
                    new[k] = float(row[k])
            if not row:
                changes.append(f"{gid}: new row {os.path.basename(new['file'])} {new['start']:.4f} → {new['end']:.4f} V{new['track'] + 1}")
            for k, v in new.items():
                if row and row.get(k) != v:
                    changes.append(f'{gid}: {k} {row.get(k)!r} → {v!r}')
            out.append(new)
        # track assignment: a row overlapping an earlier V3 row goes to V4
        placed3 = []
        for r in out:
            if r['track'] == 2 and any(r['start'] < p['end'] - 1e-3 and p['start'] < r['end'] - 1e-3 for p in placed3):
                r['track'] = 3; changes.append(f"{r['id']}: overlaps a V3 graphic → V4")
            if r['track'] == 2: placed3.append(r)
        return out, [c for c in changes if c]

    # ── the timeline, read back ─────────────────────────────────────────────
    def readback(self):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; if (!seq) return "ERROR: no active sequence";
  var out = [];
  for (var t = 2; t < seq.videoTracks.numTracks; t++) {
    var tr = seq.videoTracks[t];
    for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
      out.push({track: t, name: c.name, start: c.start.seconds, end: c.end.seconds,
                path: c.projectItem ? c.projectItem.getMediaPath() : ""}); }
  }
  return JSON.stringify(out);
})()""")
        if str(r).startswith('ERROR'): sys.exit(r)
        return json.loads(r)

    def verify(self, quiet=False):
        F = self.F()
        tl = self.readback()
        ok = True
        seen = set()
        for r in self.rows:
            hit = [c for c in tl if os.path.basename(c['path']) == os.path.basename(r['file'])]
            m = [c for c in hit if abs(c['start'] - r['start']) <= 1.5 * F]
            if not m:
                ok = False
                if hit: print(f"✗ {r['id']}: {os.path.basename(r['file'])} is on the timeline at {hit[0]['start']:.4f}, placement says {r['start']:.4f}")
                else: print(f"✗ {r['id']}: {os.path.basename(r['file'])} not on V3/V4")
                continue
            c = m[0]; seen.add(id(c))
            if abs(c['end'] - r['end']) > 1.5 * F:
                ok = False; print(f"✗ {r['id']}: ends {c['end']:.4f} on the timeline, placement says {r['end']:.4f} ({(c['end'] - r['end']) / F:+.1f} frames)")
            elif c['track'] != r.get('track', 2):
                ok = False; print(f"✗ {r['id']}: on V{c['track'] + 1}, placement says V{r.get('track', 2) + 1}")
            elif not quiet:
                print(f"✓ {r['id']:<5} V{c['track'] + 1} {c['start']:.4f} → {c['end']:.4f}  {os.path.basename(c['path'])}")
        extra = [c for c in tl if id(c) not in seen and c['name'] != 'GRADE']
        for c in extra:
            print(f"⚠ extra clip on V{c['track'] + 1}: {c['name']} {c['start']:.4f} → {c['end']:.4f} ({os.path.basename(c['path'])}): not in placement.json")
        print(f"{'ALL PLACED' if ok else 'DRIFT'}: {len(self.rows)} rows, {len(extra)} extra clip(s)")
        return ok

    # ── writes ──────────────────────────────────────────────────────────────
    def remove(self, gid, path_base=None):
        r = es(r"""
(function(){
  var seq = app.project.activeSequence; var GID = %s, BASE = %s; var removed = [];
  for (var t = 2; t < seq.videoTracks.numTracks; t++) {
    var tr = seq.videoTracks[t];
    for (var i = tr.clips.numItems - 1; i >= 0; i--) { var c = tr.clips[i];
      var p = c.projectItem ? c.projectItem.getMediaPath() : ""; var b = p.split("/").pop();
      var mine = BASE ? (b === BASE) : (b.indexOf(GID + "-") === 0 || b.indexOf(GID + ".") === 0);
      if (!mine) continue;
      var ok = false;
      try { ok = c.remove(false, false); } catch (e) { ok = false; }
      if (!ok) { app.enableQE(); var qt = qe.project.getActiveSequence().getVideoTrackAt(t);
        for (var q = qt.numItems - 1; q >= 0; q--) { var it = qt.getItemAt(q);
          if (it.type === "Clip" && Math.abs(it.start.secs - c.start.seconds) < 0.002) { it.remove(false, false); ok = true; break; } } }
      removed.push(b + "@" + c.start.seconds.toFixed(3) + (ok ? "" : " (FAILED)"));
    }
  }
  return JSON.stringify(removed);
})()""" % (json.dumps(gid), json.dumps(path_base)))
        return json.loads(r)

    def place(self, r):
        F = self.F()
        out = es(r"""
(function(){
  var seq = app.project.activeSequence, root = app.project.rootItem;
  var PATH = %s, START = %s, END = %s, TRACK = %s;
  function findByPath(bin){ for (var i = 0; i < bin.children.numItems; i++) { var c = bin.children[i];
    if (c.type === ProjectItemType.BIN) { var f = findByPath(c); if (f) return f; }
    else if (c.getMediaPath && c.getMediaPath() === PATH) return c; } return null; }
  var item = findByPath(root);
  if (!item) { app.project.importFiles([PATH], true, root, false); item = findByPath(root); }
  if (!item) return "ERROR: import failed for " + PATH;
  var tr = seq.videoTracks[TRACK];
  tr.overwriteClip(item, START + %s);
  var clip = null;
  for (var i = 0; i < tr.clips.numItems; i++) { var c = tr.clips[i];
    if (Math.abs(c.start.seconds - START) < 0.02 && c.projectItem && c.projectItem.getMediaPath() === PATH) clip = c; }
  if (!clip) return "ERROR: clip did not land on V" + (TRACK + 1) + " at " + START;
  if (clip.end.seconds > END + 0.0005) { var t = new Time(); t.seconds = END + %s; clip.end = t; }
  return JSON.stringify({start: clip.start.seconds, end: clip.end.seconds, name: clip.name});
})()""" % (json.dumps(r['file']), r['start'], r['end'], r.get('track', 2), NUDGE, NUDGE))
        if str(out).startswith('ERROR'): sys.exit(f"{r['id']}: {out}")
        got = json.loads(out)
        if abs(got['start'] - r['start']) > 1.5 * F or abs(got['end'] - r['end']) > 1.5 * F:
            sys.exit(f"{r['id']}: placed {got['start']:.4f} → {got['end']:.4f} but wanted {r['start']:.4f} → {r['end']:.4f} (readback mismatch, stopping)")
        return got

    def apply(self):
        F = self.F()
        tl = self.readback()
        placed, swapped, kept = [], [], []
        for r in self.rows:
            base = os.path.basename(r['file'])
            same = [c for c in tl if os.path.basename(c['path']) == base and abs(c['start'] - r['start']) <= 1.5 * F
                    and abs(c['end'] - r['end']) <= 1.5 * F and c['track'] == r.get('track', 2)]
            if same: kept.append(r['id']); continue
            stale = [c for c in tl if os.path.basename(c['path']) != base and
                     re.match(r'%s[-.]' % re.escape(r['id']), os.path.basename(c['path']))]
            if stale:
                gone = self.remove(r['id'])
                swapped.append(f"{r['id']}: removed {gone}")
            got = self.place(r)
            placed.append(f"{r['id']}: V{r.get('track', 2) + 1} {got['start']:.4f} → {got['end']:.4f} {base}")
        for s in swapped: print('↻ ' + s)
        for p in placed: print('+ ' + p)
        print(f"{len(kept)} already placed · {len(placed)} placed · {len(swapped)} swapped")
        if placed or swapped:
            sh('node', str(BRIDGE), 'save_project')
            print('saved')
            self.verify(quiet=True)

    def sync_plan(self):
        F = self.F()
        rows = {r['id']: r for r in self.rows}
        n = 0
        for b in self.plan['beats']:
            r = rows.get(b.get('id'))
            if not r: continue
            for k in ('start', 'end'):
                if abs(float(b[k]) - r[k]) > 1e-4:
                    print(f"{b['id']}: {k} {float(b[k]):.4f} → {r[k]:.4f} ({(r[k] - float(b[k])) / F:+.2f} frames)")
                    b[k] = r[k]; n += 1
        if n:
            json.dump(self.plan, open(self.plan_p, 'w'), indent=1)
            print(f'graphics-plan.json: {n} value(s) synced to the placement')
        else:
            print('graphics-plan.json already matches placement.json')


def main():
    a = sys.argv[1:]
    if len(a) < 2: sys.exit(__doc__)
    p = Placer(a[0])
    if '--plan' in a:
        rows, changes = p.derive()
        for c in changes: print('  ' + c)
        if '--write' in a:
            json.dump(rows, open(p.pj, 'w'), indent=1); print(f'wrote {len(rows)} rows -> {p.pj}')
        else:
            print(f'{len(rows)} rows derived, {len(changes)} change(s) vs placement.json (add --write to save)')
    elif '--verify' in a:
        sys.exit(0 if p.verify() else 1)
    elif '--apply' in a:
        p.apply()
    elif '--remove' in a:
        print(p.remove(a[a.index('--remove') + 1]))
    elif '--sync-plan' in a:
        p.sync_plan()
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
