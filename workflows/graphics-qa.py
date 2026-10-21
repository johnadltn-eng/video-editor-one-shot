#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""graphics-qa.py: the build-time QA gate between the graphics BUILD (5b) and the REVIEW loop (5c).

  uv run workflows/graphics-qa.py projects/<job> [--ids g1,g2] [--json hf-graphics/qa-report.json] [--fps 24000/1001]
  (uv resolves numpy from the header above; plain python3 works where numpy is installed)

Exit 1 on any FAIL: the handoff to edit-review is blocked until it is green. Everything it owns is
OFF-LIMITS to the LLM reviewers, they review intent, copy and depiction; this sweeps every frame.

Why (2026-09-02, your-job): 17 of the 21 defects five Opus review rounds found were
deterministic: a rise-out landing a frame short, a float missing, a rise-in dipping under the
band, an em dash in a label, a placed end 42 ms off its V1 cut. ~100 minutes and ~5.8M tokens for
what this runs in under a minute, on the local renders alone, no editor round-trip.

Inputs (all in the job folder): hf-graphics/placement.json (the placement manifest, one row per placed
graphic: {id, file, start, end, kind: text|full|overlay, track}; the Premiere lane's place-graphics.py
writes it, any other lane writes the same rows by hand before running this),
graphics-plan.json, transcript/cuts.json (V1 cut points = cumulative kept durations), the comps under
hf-graphics/*/compositions/, the renders those rows point at, and hf-graphics/qa-waivers.json:
  {"g18": {"band": "DOWN arrow: its lowest bounce frame sits ON y1030 by design"}}
A waiver replaces a prose "deliberate deviation" in the build report: it is machine-read, named per
check, and shows in the report as `waived`, so a reviewer cannot dismiss a real defect on the strength
of a sentence (round 2 dismissed a real 83 ms cut-end flash that way).

Checks (per placed graphic unless noted):
  render     file exists · overlay = ProRes 4444 alpha, full-screen = opaque mp4 · fps == the timeline's
  duration   placed length vs the render's, within 1.5 frames (a trim means an exit was cut off)
  band       overlays: no ink below the band floor (y1030), none within 100 px of the left/right/top edge,
             low-band graphics never above the band top, EVERY frame of the render (alpha sweep)
  exit       overlays: the last rendered frame is EMPTY (hard-kill) unless the V1 cut is the exit
  lead       full-screens: static lead frames before the first element arrives (frame-0 rule)
  grain      full-screens carry the film-grain pass (section titles are exempt)
  cut        a full-screen (or a text animation whose exit is the cut) that ends within 8 frames of a V1
             cut must end ON it, to the frame, off by one it flashes the outgoing shot; ending far
             from any cut (a cut back mid-take, g14) is a choice and passes
  holes      overlays on one track: overlaps (FAIL) and sub-3-frame gaps between neighbours (warn)
  plan       every plan graphic is placed and vice versa; start/end agree within 1.5 frames
  copy       text-animation phrase == the plan's copy · no U+2014 anywhere on screen or in the plan
  source     hand comps: helpers defined or hf-anim.js loaded · registry constants exact · riseOut
             relative · float() on a wrapper over 0 → DUR · 12 fps form on bg-dark · no flash at 12 fps
             · no Math.random / onUpdate · content reveals pin the zero frame · arrowheads computed ·
             position:absolute with no offsets · exits never before entrances
  density    (job) events/min, longest bare stretch, full-screen share, same full-screen twice in a row
Not here (the reviewers own them): copy meaning, depiction (card vs scene), asset contrast on its plate,
glow spill outside a prop's box, reveal burst cadence on the render.
"""
import json, os, re, subprocess, sys, glob, math
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

try:
    import numpy as np
except ImportError:
    sys.exit("graphics-qa.py needs numpy (brew install numpy, or `uv run --with numpy,pillow`)")

BAND_FLOOR, EDGE, TOP_EDGE = 1030, 100, 100
ALPHA_INK = 160           # 0-255 on a 4x-downscaled alpha plane: solid ink: a glow or shadow bleeding past the box is not ink
ALPHA_ANY = 40            # anything at all (the last-frame emptiness check)
GRAIN_MIN = 0.9           # mean |frame − 3x3 median| on a full-screen's first frame; the grain pass sits ~2-4
DENSITY = dict(per_min=(11, 13), bare_max=6.0, full_pct_max=25.0)
REGISTRY = {  # the numbers an INLINE helper block must carry (skipped when hf-anim.js is loaded)
    'DRAW': ['DRAW = 9'],
    'float': ['subtle: [6, 8, 1.25, 0.95]', 'medium: [10, 16, 1.35, 1.05]'],
    'riseIn': ['dist = 22', '0.55', 'power3.out'],
    'riseOut': ['dist = 18', '0.35', 'power2.in'],
    'pop': ['0.90', '1.10', '3*F', 'power2.out'],
    'slam': ['1.16', 'power2.out'],
}
HELPERS = ('pop', 'slam', 'flash', 'riseIn', 'riseOut', 'slideIn', 'slideOut', 'float', 'arrow', 'drawOn', 'countUp', 'reveal', 'exit')
ENTRANCES = ('pop', 'slam', 'flash', 'riseIn', 'slideIn', 'drawOn')
EXITS = ('riseOut', 'slideOut', 'exit')


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = sh('ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
           'stream=pix_fmt,r_frame_rate,nb_frames,duration', '-of', 'json', path)
    if r.returncode: return None
    s = json.loads(r.stdout)['streams'][0]
    num, _, den = s['r_frame_rate'].partition('/')
    return dict(pix=s.get('pix_fmt'), fps=float(num) / float(den or 1),
                frames=int(s.get('nb_frames') or 0), dur=float(s.get('duration') or 0))


def frames(path, vf, w, h, pix='gray', n_frames=None):
    """Yield numpy frames from ffmpeg (rawvideo pipe)."""
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', vf] + (['-frames:v', str(n_frames)] if n_frames else [])
                         + ['-f', 'rawvideo', '-pix_fmt', pix, '-'], stdout=subprocess.PIPE)
    n = w * h * (1 if pix == 'gray' else 3)
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(h, w) if pix == 'gray' else np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def norm_words(s):
    return [re.sub(r"^[^\w']+|[^\w']+$", '', w).lower() for w in re.sub(r'[*~]', '', s).split() if re.sub(r"[^\w']", '', w)]


class QA:
    def __init__(self, job, fps=None, ids=None):
        self.job = Path(job).resolve()
        self.hf = self.job / 'hf-graphics'
        pj = self.hf / 'placement.json'
        if not pj.exists():
            sys.exit(f'{pj} missing: the placement manifest (see the docstring). Premiere lane: '
                     'uv run lanes/premiere/place-graphics.py <job> --plan --write; other lanes write the same rows by hand.')
        self.rows = json.load(open(pj))
        for r in self.rows:
            if r.get('kind') == 'alpha': r['kind'] = 'overlay'     # older rows named the format, not the role
        if ids: self.rows = [r for r in self.rows if r['id'] in ids]
        self.plan = json.load(open(self.job / 'graphics-plan.json'))
        self.cells = {b['id']: b for b in self.plan['beats'] if b.get('graphic')}
        wp = self.hf / 'qa-waivers.json'
        self.waivers = json.load(open(wp)) if wp.exists() else {}
        self.findings = []       # (id, check, level, msg)
        self.band_top = (self.plan.get('low_band') or {}).get('top', 765)
        cuts, t = [], 0.0
        cp = self.job / 'transcript' / 'cuts.json'
        if cp.exists():
            for s in json.load(open(cp))['segments']:
                t += float(s['end']) - float(s['start']); cuts.append(t)
        self.cuts = cuts
        self.fps = fps
        self.text_meta = {}
        for m in glob.glob(str(self.hf / '*' / 'compositions' / '*.meta.json')):
            self.text_meta[Path(m).name.replace('.meta.json', '')] = json.load(open(m))

    def note(self, gid, check, level, msg):
        w = (self.waivers.get(gid) or {}).get(check)
        if w and level == 'FAIL':
            level, msg = 'waived', f'{msg}  [waived: {w}]'
        self.findings.append((gid, check, level, msg))

    def comp(self, gid):
        for p in glob.glob(str(self.hf / '*' / 'compositions' / f'{gid}.html')):
            return Path(p)
        return None

    def cut_miss(self, t, window=8):
        """The V1 cut this time nearly lands on but misses, or None. A boundary within `window`
        frames of a cut is meant to sit ON it (off by one = a flash of the other shot); a boundary
        far from every cut is a cut back mid-take, which is a choice, not a miss."""
        if not self.cuts: return None
        f = 1.0 / self.fps
        c = min(self.cuts, key=lambda x: abs(x - t))
        return c if 0.6 * f < abs(t - c) <= window * f else None

    # ── per graphic ──────────────────────────────────────────────────────────
    def check_row(self, r):
        gid, f = r['id'], r['file']
        if not os.path.exists(f):
            self.note(gid, 'render', 'FAIL', f'render missing: {f}'); return
        pr = probe(f)
        if not pr: self.note(gid, 'render', 'FAIL', f'ffprobe cannot read {f}'); return
        if self.fps is None: self.fps = pr['fps']
        if abs(pr['fps'] - self.fps) > 0.01:
            self.note(gid, 'render', 'FAIL', f"render fps {pr['fps']:.3f} != timeline {self.fps:.3f}")
        F = 1.0 / self.fps
        full = r.get('kind') == 'full'
        if full and pr['pix'] and pr['pix'].startswith('yuva'):
            self.note(gid, 'render', 'FAIL', 'a full-screen graphic must be an OPAQUE mp4 (this has alpha)')
        if not full and pr['pix'] != 'yuva444p12le':
            self.note(gid, 'render', 'FAIL', f"overlay must be ProRes 4444 straight alpha (yuva444p12le), got {pr['pix']}")
        placed = r['end'] - r['start']
        if abs(placed - pr['dur']) > 1.5 * F:
            self.note(gid, 'duration', 'warn', f"placed {placed:.3f}s vs render {pr['dur']:.3f}s "
                      f"({(pr['dur'] - placed) / F:+.1f} frames): a trimmed tail cuts the exit off; extended = a frozen last frame")
        cell = self.cells.get(gid)
        meta = self.text_meta.get(gid, {})
        # band / edge / exit sweep on the alpha plane (overlays only)
        if not full:
            self.sweep_alpha(gid, f, r, cell, meta, F)
        else:
            self.sweep_full(gid, f, r, cell, F)
        # cut alignment
        if full or meta.get('exit') == 'cut':
            for edge in (('end', r['end']),) + ((('start', r['start']),) if full else ()):
                miss = self.cut_miss(edge[1])
                if miss is not None:
                    self.note(gid, 'cut', 'FAIL', f"{edge[0]} {edge[1]:.4f} is {(edge[1] - miss) / F:+.2f} frames off the V1 cut at {miss:.4f}: "
                              f"the other shot flashes for those frames, sit exactly on the cut")
        # plan reconciliation
        if not cell:
            self.note(gid, 'plan', 'FAIL', 'placed but not a graphic:true cell in graphics-plan.json')
        else:
            for k in ('start', 'end'):
                if abs(float(cell[k]) - float(r[k])) > 1.5 * F:
                    self.note(gid, 'plan', 'FAIL', f"plan {k} {float(cell[k]):.3f} vs placed {float(r[k]):.3f} "
                              f"({(float(r[k]) - float(cell[k])) / F:+.1f} frames): run place-graphics.py --sync-plan or fix the placement")
            if '—' in (cell.get('copy') or '') or '—' in (cell.get('content') or '')[:0]:
                self.note(gid, 'copy', 'FAIL', 'em dash (U+2014) in the plan copy')
            if r.get('kind') == 'text':
                self.check_text_copy(gid, cell)
        # source lints on hand comps
        c = self.comp(gid)
        if c and r.get('kind') != 'text':
            self.lint_comp(gid, c, cell, full)
        elif c and r.get('kind') == 'text':
            src = c.read_text()
            if 'data-w="' in src:
                for w in re.findall(r'data-w="([^"]*)"', src):
                    if '*' in w or '~' in w or '—' in w:
                        self.note(gid, 'copy', 'FAIL', f'literal marker/em dash on screen: {w!r}')

    def sweep_alpha(self, gid, f, r, cell, meta, F):
        w, h = 480, 1080
        low_band = (cell or {}).get('region') == 'low-band' or r.get('kind') == 'text'
        # an element that SLIDES in or out crosses the frame edge by definition: the left/right edge
        # rule holds on its hold, not while it is passing through
        c = self.comp(gid)
        js = c.read_text() if c else ''
        slide_in = 0.75 if 'slideIn(' in js else 0.0
        slide_out = 0.38 if 'slideOut(' in js else 0.0
        worst = dict(bottom=(-1, -1), top=(10**6, -1), left=(10**6, -1), right=(-1, -1), topedge=(10**6, -1))
        last = None; n = 0
        total = probe(f)['frames'] or 0
        for i, fr in enumerate(frames(f, f'alphaextract,scale={w}:{h}', w, h)):
            n += 1; last = fr
            ys, xs = np.where(fr > ALPHA_INK)
            if ys.size == 0: continue
            b, t, l, rr = int(ys.max()), int(ys.min()), int(xs.min()) * 4, int(xs.max()) * 4
            if b > worst['bottom'][0]: worst['bottom'] = (b, i)
            if t < worst['top'][0]: worst['top'] = (t, i)
            passing = (i * F < slide_in) or (total and (total - 1 - i) * F < slide_out)
            if not passing:
                if l < worst['left'][0]: worst['left'] = (l, i)
                if rr > worst['right'][0]: worst['right'] = (rr, i)
        if n == 0:
            self.note(gid, 'render', 'FAIL', 'no frames decoded'); return
        b, bi = worst['bottom']
        if b > BAND_FLOOR:
            self.note(gid, 'band', 'FAIL', f'ink reaches y{b} (floor {BAND_FLOOR}) at frame {bi} ({bi * F + r["start"]:.3f}s)')
        t, ti = worst['top']
        if low_band and t < self.band_top:
            self.note(gid, 'band', 'FAIL', f'low-band graphic has ink at y{t} (band top {self.band_top}, chin clearance) at frame {ti}')
        if not low_band and t < TOP_EDGE:
            self.note(gid, 'band', 'FAIL', f'ink within {TOP_EDGE}px of the top edge (y{t}) at frame {ti}')
        l, li = worst['left']
        if l < EDGE: self.note(gid, 'band', 'FAIL', f'ink within {EDGE}px of the left edge (x{l}) at frame {li}')
        rr, ri = worst['right']
        if rr > 1920 - EDGE: self.note(gid, 'band', 'FAIL', f'ink within {EDGE}px of the right edge (x{rr}) at frame {ri}')
        # an overlay that ends ON a V1 cut may use the cut as its exit (a text animation says so in
        # its meta; a hand comp says so by ending there, g4's FREE chip holds to the cut by design)
        on_cut = meta.get('exit') == 'cut' or (self.cuts and min(abs(r['end'] - c) for c in self.cuts) <= 0.6 * F)
        if not on_cut and last is not None and int(last.max()) > ALPHA_ANY:
            self.note(gid, 'exit', 'FAIL', f'last rendered frame still carries ink (alpha max {int(last.max())}): '
                      'the exit did not complete (fade ending AT DUR instead of 2 frames before) or the hard-kill is missing')

    def sweep_full(self, gid, f, r, cell, F):
        w, h = 64, 36
        seq = list(frames(f, f'scale={w}:{h}', w, h))
        if not seq: self.note(gid, 'render', 'FAIL', 'no frames decoded'); return
        diffs = [float(np.abs(seq[i].astype(int) - seq[i - 1].astype(int)).mean()) for i in range(1, min(16, len(seq)))]
        lead = 0
        for d in diffs:
            if d < 1.0: lead += 1
            else: break
        if lead >= 2 and any(d > 2.5 for d in diffs):
            self.note(gid, 'lead', 'warn', f'{lead} static lead frames before the first element arrives, a defect if that '
                      'element is near-full-frame (animations.md § frame 0), fine for a small first element')
        # grain: residual against a 3x3 median on the first frame at half res
        g0 = next(frames(f, 'scale=960:540', 960, 540, n_frames=1))
        med = np.median(np.stack([np.roll(np.roll(g0, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]), axis=0)
        resid = float(np.abs(g0.astype(float) - med).mean())
        is_title = (cell or {}).get('template', '').startswith('section') or (cell or {}).get('kind') == 'section-title'
        if resid < GRAIN_MIN and not is_title:
            self.note(gid, 'grain', 'FAIL', f'no film-grain pass on this full-screen (residual {resid:.2f} < {GRAIN_MIN})')

    def check_text_copy(self, gid, cell):
        tj = self.hf / 'text-animation' / 'text.json'
        if not tj.exists(): return
        spec = json.load(open(tj)).get(gid)
        if not spec: self.note(gid, 'copy', 'FAIL', 'text animation has no entry in text.json'); return
        shown = spec.get('display') or spec['phrase']
        if norm_words(shown) != norm_words(cell.get('copy') or ''):
            self.note(gid, 'copy', 'FAIL', f"on-screen words {' '.join(norm_words(shown))!r} != plan copy "
                      f"{' '.join(norm_words(cell.get('copy') or ''))!r} (reconcile the plan or the spec)")

    def lint_comp(self, gid, path, cell, full):
        src = path.read_text()
        js = ''.join(re.findall(r'<script>(.*?)</script>', src, re.S))
        js = re.sub(r'/\*.*?\*/', '', js, flags=re.S)
        js = re.sub(r'(^|[^:\\])//[^\n]*', r'\1', js)          # comments are not code ("never onUpdate" matched once)
        css = ''.join(re.findall(r'<style>(.*?)</style>', src, re.S))
        body = re.search(r'<body[^>]*>(.*)</body>', src, re.S)
        body = body.group(1) if body else src
        body = re.sub(r'<(script|style)>.*?</\1>', '', body, flags=re.S)
        body = re.sub(r'<!--.*?-->', '', body, flags=re.S)
        visible = re.sub(r'<[^>]+>', ' ', body)
        if '—' in visible: self.note(gid, 'copy', 'FAIL', 'em dash (U+2014) in on-screen text')
        uses_hf = 'hf-anim.js' in src
        used = {h for h in HELPERS if re.search(r'\b%s\s*\(' % h, js)}
        if not uses_hf:
            for h in used:
                if not re.search(r'\b(const|let|var|function)\s+%s\b' % h, js):
                    self.note(gid, 'source', 'FAIL', f'calls {h}() but never defines it and does not load hf-anim.js (renders blank)')
            for name, needles in REGISTRY.items():
                defined = re.search(r'\b(const|let|var|function)\s+%s\b' % name, js)
                if not defined: continue
                if name in ('pop', 'slam') and (full and (cell or {}).get('bg') == 'dark'): continue   # the 12 fps form is checked below
                missing = [n for n in needles if n.replace(' ', '') not in js.replace(' ', '')]
                if missing:
                    self.note(gid, 'source', 'FAIL', f'inline {name} drifts from the registry: {", ".join(missing)} not found (animations.md): load hf-anim.js instead of retyping')
            m = re.search(r'riseOut\s*=\s*\([^)]*\)\s*=>\s*\{.*?\n|riseOut\s*=\s*\([^)]*\)\s*=>\s*\{[^\n]*', js)
            if m and "'-='" not in m.group(0) and '"-="' not in m.group(0):
                self.note(gid, 'source', 'FAIL', 'riseOut writes an ABSOLUTE y: an element resting off 0 exits the wrong way; use y: "-=" + dist')
        if 'float' not in used:
            self.note(gid, 'source', 'FAIL', 'no float() call: every hand graphic carries THE FLOAT for its whole life (creative-moves.md move 2)')
        else:
            for sel, t0, t1, preset in re.findall(r"float\(\s*'([^']+)'\s*,\s*([^,]+),\s*([^,]+),\s*'(\w+)'\s*\)", js):
                if t0.strip() != '0' or t1.strip() != 'DUR':
                    self.note(gid, 'source', 'warn', f'float({sel}) spans {t0.strip()} → {t1.strip()}, not 0 → DUR')
                if preset not in ('subtle', 'medium'):
                    self.note(gid, 'source', 'FAIL', f'float preset {preset!r} is not subtle|medium')
                sid = sel.lstrip('#.')
                blk = re.search(r'[#.]%s\b[^{]*\{([^}]*)\}' % re.escape(sid), css)
                if blk and 'inset:0' not in blk.group(1).replace(' ', '') and 'position:absolute' not in blk.group(1).replace(' ', ''):
                    self.note(gid, 'source', 'warn', f'float wrapper {sel} is not a position:absolute;inset:0 wrapper')
        dark = full and (cell or {}).get('bg') == 'dark'
        if dark:
            if 'flash(' in js or 'flicker' in js:
                self.note(gid, 'source', 'FAIL', 'flash on a 12 fps graphic (its single-frame gaps vanish), pop or slam')
            if uses_hf and not re.search(r'stepFps\s*:\s*12', js):
                self.note(gid, 'source', 'FAIL', 'bg-dark full-screen loads hf-anim.js without stepFps: 12 (pop/slam will be authored in timeline frames)')
            if not uses_hf and ('pop(' in js or 'slam(' in js) and not re.search(r'S12|SF\b|/\s*12\b|\* 12\)', js):
                self.note(gid, 'source', 'FAIL', 'pop/slam authored in timeline frames on a 12 fps comp, re-express in 83 ms states (or load hf-anim.js with stepFps: 12)')
        if 'Math.random' in js: self.note(gid, 'source', 'FAIL', 'Math.random in a comp: the headless render seeks, so every pass differs')
        if 'onUpdate' in js: self.note(gid, 'source', 'FAIL', 'onUpdate-driven content renders FROZEN headless (never fires on seek)')
        if 'innerText' in js and not re.search(r'innerText[^}]*\}\s*,\s*0\s*\)', js) and 'countUp(' not in js and 'reveal(' not in js:
            self.note(gid, 'source', 'FAIL', 'content reveal (innerText) has no zero-frame pin: tl.set(el, {innerText: ...}, 0)')
        if re.search(r'<polygon[^>]*class="[^"]*\bhead\b[^"]*"[^>]*points=', src):
            self.note(gid, 'source', 'FAIL', 'hand-typed arrowhead points: heads ship empty and arrow() computes them from the end tangent')
        if re.search(r'<polygon[^>]*class="[^"]*\bhead\b', src) and 'arrow(' not in js:
            self.note(gid, 'source', 'FAIL', 'arrow head present but arrow() never called (head never gets points)')
        for sel, blk in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
            b = blk.replace(' ', '')
            if 'position:absolute' in b and not re.search(r'\b(left|right|top|bottom|inset)\s*:', blk) and 'root' not in sel:
                self.note(gid, 'source', 'warn', f'{sel.strip()[:40]} is position:absolute with no offsets (lands at 0,0 of its parent, the g3 check-dot bug)')
        # exits never before entrances (numeric or simple expressions)
        env = {}
        for name, val in re.findall(r'const\s+(DUR|F|SF|S12)\s*=\s*([^,;]+)', js):
            try: env[name] = eval(val, {'__builtins__': {}}, dict(env))
            except Exception: pass
        def ev(expr):
            try: return float(eval(expr, {'__builtins__': {}}, dict(env)))
            except Exception: return None
        ins, outs = {}, {}
        for fn, sel, t in re.findall(r"\b(%s)\(\s*'([^']+)'\s*,\s*([^,)]+)" % '|'.join(ENTRANCES + EXITS), js):
            v = ev(t.strip())
            if v is None: continue
            (ins if fn in ENTRANCES else outs).setdefault(sel, []).append(v)
        for sel, ts in outs.items():
            if sel in ins and min(ts) < min(ins[sel]):
                self.note(gid, 'source', 'FAIL', f'{sel} exits at {min(ts):.2f}s before it enters at {min(ins[sel]):.2f}s')

    # ── job-wide ─────────────────────────────────────────────────────────────
    def check_job(self):
        F = 1.0 / self.fps
        rows = sorted(self.rows, key=lambda r: r['start'])
        by_track = {}
        for r in rows: by_track.setdefault(r.get('track', 2), []).append(r)
        for t, rs in by_track.items():
            for a, b in zip(rs, rs[1:]):
                gap = b['start'] - a['end']
                if gap < -0.3 * F:
                    self.note(b['id'], 'holes', 'FAIL', f"overlaps {a['id']} on V{t + 1} by {-gap / F:.1f} frames (overwriteClip would eat the earlier clip)")
                elif 0.3 * F < gap < 3 * F:
                    self.note(b['id'], 'holes', 'warn', f"{gap / F:.1f}-frame hole between {a['id']} and {b['id']} on V{t + 1}, butt-join them or mean the gap")
        placed = {r['id'] for r in self.rows}
        for gid in self.cells:
            if gid not in placed and not self.only_ids:
                self.note(gid, 'plan', 'FAIL', 'graphic:true in the plan but not in placement.json')
        # density
        dur = float(self.plan.get('duration') or (rows[-1]['end'] if rows else 0)) or 1
        per_min = len(rows) / (dur / 60)
        bare, prev_end = 0.0, 0.0
        for r in rows:
            bare = max(bare, r['start'] - prev_end); prev_end = max(prev_end, r['end'])
        bare = max(bare, dur - prev_end)
        full_s = sum(r['end'] - r['start'] for r in rows if r.get('kind') == 'full')
        msg = (f"{len(rows)} events over {dur:.1f}s = {per_min:.1f}/min · longest bare stretch {bare:.1f}s · "
               f"full-screens {full_s:.1f}s = {100 * full_s / dur:.1f}% of runtime")
        lvl = 'info'
        if not (DENSITY['per_min'][0] <= per_min <= DENSITY['per_min'][1] + 0.5) or bare > DENSITY['bare_max'] or 100 * full_s / dur > DENSITY['full_pct_max']:
            lvl = 'warn'
        self.note('job', 'density', lvl, msg)
        fulls = [r for r in rows if r.get('kind') == 'full']
        for a, b in zip(fulls, fulls[1:]):
            ca, cb = self.cells.get(a['id'], {}), self.cells.get(b['id'], {})
            if ca.get('bg') and ca.get('bg') == cb.get('bg') and not any(r['start'] > a['end'] and r['end'] < b['start'] for r in rows if r.get('kind') != 'full'):
                self.note(b['id'], 'density', 'warn', f"same full-screen field ({ca['bg']}) as {a['id']} with nothing between (anti-stale law)")

    def run(self, only_ids=None):
        self.only_ids = only_ids
        for r in self.rows:
            self.check_row(r)
        if self.fps is None: sys.exit('no readable render: cannot determine the timeline fps')
        self.check_job()
        return self.findings


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    job = a[0]
    ids = None; out = None; fps = None
    if '--ids' in a: ids = a[a.index('--ids') + 1].split(',')
    if '--json' in a: out = a[a.index('--json') + 1]
    if '--fps' in a:
        num, _, den = a[a.index('--fps') + 1].partition('/'); fps = float(num) / float(den or 1)
    qa = QA(job, fps, ids)
    findings = qa.run(ids)
    fails = [f for f in findings if f[2] == 'FAIL']
    for gid in sorted({f[0] for f in findings}, key=lambda g: (g != 'job', g)):
        fs = [f for f in findings if f[0] == gid]
        mark = '✗' if any(f[2] == 'FAIL' for f in fs) else ('·' if all(f[2] == 'info' for f in fs) else '⚠')
        print(f'{mark} {gid}')
        for _, check, level, msg in fs:
            print(f'    {level:<6} {check:<8} {msg}')
    clean = [r['id'] for r in qa.rows if r['id'] not in {f[0] for f in findings}]
    if clean: print('✓ clean: ' + ' '.join(clean))
    print(f"\n{len(fails)} FAIL · {sum(1 for f in findings if f[2] == 'warn')} warn · "
          f"{sum(1 for f in findings if f[2] == 'waived')} waived · {len(qa.rows)} graphics · fps {qa.fps:.3f}")
    if out:
        json.dump({'job': str(qa.job), 'fps': qa.fps, 'graphics': [r['id'] for r in qa.rows],
                   'findings': [dict(id=g, check=c, level=l, msg=m) for g, c, l, m in findings],
                   'waivers': qa.waivers}, open(out, 'w'), indent=1)
        print(f'report -> {out}')
    if fails:
        sys.exit(1)


if __name__ == '__main__':
    main()
