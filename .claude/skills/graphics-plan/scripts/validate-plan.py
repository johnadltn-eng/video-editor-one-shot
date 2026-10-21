#!/usr/bin/env python3
"""validate-plan.py: the hard gate at graphics-plan Step 5: a plan that fails here is not written.

  uv run .claude/skills/graphics-plan/scripts/validate-plan.py projects/<job> [--fps 24000/1001]

Exit 1 on any FAIL. Checks (2026-09-02, from the your-job retro, every one is a defect
the build or the review loop later paid for):
  anchor    a text-animation cell STARTS on the first word of its own copy (word.start − 0.08 lead,
            within 0.15s): not on the sentence, not on a guess (g18b, g6)
  cut       a full-screen / punch-cut edge within 8 frames of a cuts.json boundary sits ON it to the
            frame: a rounded end flashes the outgoing shot (g2 83 ms, g11 42 ms, g7 25 ms); an edge
            far from any cut is a cut back mid-take and passes
  readable  a cell flagged "readable": true (prompt, command, code, config, quote) holds ≥ 3.0s
            (a 2s hold of the complete content plus its reveal); quote/comment kinds without the
            flag are asked about
  copy      exact, no em dash, text animations lowercase-casual (a leading capital that is not a
            proper noun is asked about), copy present on every graphic:true cell
  shape     ids unique, start < end, kind/template/region/content present, no card overlapping a card
  density   the per-minute block printed against creative-moves.md § THE DENSITY NUMBERS
"""
import json, re, sys, subprocess, glob
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

LEAD = 0.08
FULL_KINDS = {'punch-cut', 'full-screen', 'scene', 'kinetic-title'}
TEXT_KINDS = {'text-animation'}
FILLERS = {"um", "uh", "like", "you", "know", "so", "right", "okay", "ok", "actually", "basically", "just",
           "literally", "kinda", "kind", "of", "sort", "i", "mean", "yeah", "well", "and", "then"}
PROPER = {'claude', 'premiere', 'cfo', 'youtube', 'instagram', 'tiktok', 'p&l', 'ai'}   # plus any word the transcript itself capitalizes


def norm(w):
    return re.sub(r"^[^\w']+|[^\w']+$", '', w).lower()


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    job = Path(a[0]).resolve()
    fps = None
    if '--fps' in a:
        n, _, d = a[a.index('--fps') + 1].partition('/'); fps = float(n) / float(d or 1)
    if fps is None:
        raws = sorted(glob.glob(str(job / 'raw' / '*')))
        if raws:
            r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                                '-of', 'csv=p=0', raws[0]], capture_output=True, text=True).stdout.strip().split('\n')[0]
            n, _, d = r.strip(',').partition('/'); fps = float(n) / float(d or 1)
    fps = fps or 30000 / 1001
    F = 1.0 / fps
    plan = json.load(open(job / 'graphics-plan.json'))
    beats = plan['beats']
    cells = [b for b in beats if b.get('graphic')]
    words = []
    tp = job / 'outputs' / f'{job.name}.transcript.json'
    if tp.exists():
        d = json.load(open(tp)); words = [w for w in (d['words'] if isinstance(d, dict) else d) if w.get('type', 'word') == 'word']
    cuts, t = [], 0.0
    cp = job / 'transcript' / 'cuts.json'
    if cp.exists():
        for s in json.load(open(cp))['segments']:
            t += float(s['end']) - float(s['start']); cuts.append(t)
    fails, warns = [], []
    F_ = fails.append; W_ = warns.append
    # names the transcript corrections already capitalize (brands, people) are proper nouns here too
    proper = PROPER | {norm(w['text']) for w in words if w['text'][:1].isupper()}

    ids = [b['id'] for b in beats]
    for i in set(ids):
        if ids.count(i) > 1: F_(f'{i}: duplicate id')
    for c in cells:
        gid = c['id']
        for k in ('kind', 'region', 'content', 'start', 'end'):
            if k not in c: F_(f'{gid}: missing {k}')
        if 'start' in c and 'end' in c and float(c['end']) <= float(c['start']): F_(f'{gid}: end <= start')
        copy = c.get('copy') or ''
        if not copy and c.get('kind') not in ('screen-rec', 'b-roll', 'enacting-overlay', 'annotation'):
            W_(f'{gid}: no copy on a {c.get("kind")} cell (fine only if the graphic has no words)')
        if '—' in copy: F_(f'{gid}: em dash in copy {copy!r}')
        kind = c.get('kind')
        # anchor: the first word of the copy is spoken at start + LEAD
        if kind in TEXT_KINDS and words and copy:
            cw = [norm(w) for w in re.sub(r'[*~]', '', copy).split() if norm(w)]
            if cw:
                near = [w for w in words if abs(w['start'] - LEAD - float(c['start'])) <= 0.15 and norm(w['text']) == cw[0]]
                if not near:
                    cands = [w for w in words if norm(w['text']) == cw[0] and abs(w['start'] - float(c['start'])) < 3.0]
                    hint = f" ('{cw[0]}' is spoken at {', '.join(f'{w['start']:.2f}' for w in cands)}; start = word − {LEAD})" if cands else \
                           f" ('{cw[0]}' is not spoken within 3s of {float(c['start']):.2f})"
                    F_(f"{gid}: start {float(c['start']):.2f} does not anchor to the first word of its copy{hint}")
            # lowercase-casual register
            first = re.sub(r'[*~"\'(]', '', copy.split()[0]) if copy.split() else ''
            if first[:1].isupper() and first.lower() not in proper and not first.isupper():
                W_(f"{gid}: text animation starts with a capital ({first!r}), captions keep the lowercase-casual register unless it is a name")
        # cut: a full-screen edge within 8 frames of a V1 cut sits ON it (off by one flashes the
        # other shot); an edge far from every cut is a cut back mid-take, which is a choice
        if (kind in FULL_KINDS or c.get('bg')) and cuts:
            for edge in ('start', 'end'):
                t_ = float(c[edge])
                nearest = min(cuts, key=lambda x: abs(x - t_))
                if 0.5 * F < abs(nearest - t_) <= 8 * F:
                    F_(f"{gid}: full-screen {edge} {t_:.4f} is {(t_ - nearest) / F:+.2f} frames off the V1 cut at {nearest:.4f}, "
                       f"set {edge} = {nearest:.4f} exactly (off by a frame flashes the other shot)")
        # readable hold
        if c.get('readable'):
            if float(c['end']) - float(c['start']) < 3.0:
                F_(f"{gid}: readable graphic holds {float(c['end']) - float(c['start']):.2f}s, needs ≥ 3.0s (2s complete-content hold + reveal), or less text")
        elif kind in ('quote', 'comment', 'screenshot') and 'readable' not in c:
            W_(f"{gid}: a {kind} cell with no \"readable\" flag, if the viewer is meant to read it, flag it and size the slot")
    # overlaps between non-text cells (V4 exists, but a collision is a choice to state)
    ov = [c for c in cells if c.get('kind') not in TEXT_KINDS]
    for i, a1 in enumerate(ov):
        for b1 in ov[i + 1:]:
            if float(a1['start']) < float(b1['end']) and float(b1['start']) < float(a1['end']):
                W_(f"{a1['id']} and {b1['id']} overlap on the timeline ({max(float(a1['start']), float(b1['start'])):.2f} → "
                   f"{min(float(a1['end']), float(b1['end'])):.2f}): the second goes to V4; say so in content")
    # anti-stale: same template twice in a row (text animations exempt)
    seq = [c for c in sorted(cells, key=lambda c: float(c['start'])) if c.get('kind') not in TEXT_KINDS]
    for a1, b1 in zip(seq, seq[1:]):
        if a1.get('template') and a1.get('template') == b1.get('template'):
            W_(f"{b1['id']}: same template as the previous graphic {a1['id']} ({a1['template']}), the anti-stale law")
    # density block
    dur = float(plan.get('duration') or max(float(c['end']) for c in cells))
    n = len(cells); per_min = n / (dur / 60)
    texts = sum(1 for c in cells if c.get('kind') in TEXT_KINDS)
    fulls = [c for c in cells if c.get('kind') in FULL_KINDS or c.get('bg')]
    full_s = sum(float(c['end']) - float(c['start']) for c in fulls)
    push = sum(1 for c in cells if c.get('push_in'))
    bare, prev = 0.0, 0.0
    for c in sorted(cells, key=lambda c: float(c['start'])):
        bare = max(bare, float(c['start']) - prev); prev = max(prev, float(c['end']))
    bare = max(bare, dur - prev)
    print(f"density: {n} events / {dur:.1f}s = {per_min:.1f}/min (11-13) · text animations {texts} ({texts / (dur / 60):.1f}/min, 6-7) · "
          f"full-screens {len(fulls)} = {full_s:.1f}s = {100 * full_s / dur:.1f}% (≤25%) · push-ins {push} ({push / (dur / 60):.1f}/min, 1-2) · "
          f"longest bare {bare:.1f}s (≤6)")
    if per_min < 10.5: W_(f'density {per_min:.1f}/min is under the look (11-13)')
    if bare > 6.0: W_(f'longest bare stretch {bare:.1f}s > 6s')
    if 100 * full_s / dur > 25: W_(f'full-screens are {100 * full_s / dur:.1f}% of runtime (> 25%)')
    for w in warns: print(f'  warn {w}')
    for f in fails: print(f'  FAIL {f}')
    print(f"{len(fails)} FAIL · {len(warns)} warn · {n} graphics · fps {fps:.3f}")
    if fails: sys.exit(1)


if __name__ == '__main__':
    main()
