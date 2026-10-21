#!/usr/bin/env python3
"""sfx-plan.py: turn a job's PLACED graphics into an SFX plan (pipeline step 6, universal).

  uv run workflows/sfx-plan.py projects/<job>            # write hf-graphics/sfx-plan.{json,md}
  uv run workflows/sfx-plan.py projects/<job> --dry      # print the cut sheet, write nothing

Reads: hf-graphics/placement.json (the placed rows), each row's comp HTML (the registry calls it
makes and, for a text animation, its per-word spans), graphics-plan.json (the preset, the cell kinds) and
the preset's sfx.json (event -> sound -> slice -> class -> target peak). Writes one row per sound:

  {"id", "gid", "event", "at", "file", "src_in", "src_out", "level_db", "track", "cls", "note"}

`at` is the timeline time in seconds, frame-snapped. `track` is the 0-based audio track index
from the preset map (A2 primary, A3/A4 layers). `level_db` is the clip Volume Level that puts the
measured slice peak on the class target. Nothing here touches an editor; placement is per lane
(LANES.md step 6). The WHY and the numbers: presets/youtube/default/sfx.md.

Comp calls are found by a static parse of the comp's script. The `at` argument is evaluated with
the comp's own constants (F, SF, DUR, any `const NAME = <number>`); a call inside a loop over an
array literal is expanded over that array; anything else is listed under ⚠ in the cut sheet for
a hand entry, never guessed.
"""
import html as htmlmod, json, math, os, re, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CALLS = ('pop', 'slam', 'riseIn', 'riseOut', 'exit', 'slideIn', 'slideOut', 'drawOn', 'countUp', 'reveal', 'flash')
_peak_cache = {}


def slice_peak(path, a, b):
    key = (path, round(a, 3), round(b, 3))
    if key in _peak_cache: return _peak_cache[key]
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-ss', str(a), '-t', str(max(b - a, 0.05)),
                        '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True).stderr   # -ss AFTER -i: exact
    m = re.search(r'max_volume: (-?[0-9.]+)', r)
    v = float(m.group(1)) if m else 0.0
    _peak_cache[key] = v
    return v


_dur_cache = {}


def file_dur(path):
    if path not in _dur_cache:
        _dur_cache[path] = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                                capture_output=True, text=True).stdout.strip() or 0)
    return _dur_cache[path]


def probe_fps(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                        '-of', 'csv=p=0', path], capture_output=True, text=True).stdout
    n, _, d = r.strip().split('\n')[0].strip(',').partition('/')
    return float(n) / float(d or 1)


class Evaluator:
    """Evaluate a comp's time expressions with its own constants. Refuses anything it cannot bind."""
    SAFE = re.compile(r'^[\w\s+\-*/().]+$')                    # names, numbers, arithmetic, Math.round(...)

    def __init__(self, script, fps):
        self.names = {'F': 1 / fps, 'Math': type('M', (), {'round': staticmethod(lambda x: math.floor(x + 0.5)), 'floor': staticmethod(math.floor), 'ceil': staticmethod(math.ceil), 'min': staticmethod(min), 'max': staticmethod(max)})}
        for m in re.finditer(r'(?:(?:const|let|var)\s+|,\s*)(\w+)\s*=\s*([-\d.]+(?:\s*[/*+\-]\s*[-\d.]+)*)\s*(?=[;,\n])', script):
            try: self.names[m.group(1)] = eval(m.group(2), {'__builtins__': {}}, {})     # `const F = .., DUR = .., AUTO_T = ..;` binds all three
            except Exception: pass
        m = re.search(r'init\(\{([^}]*)\}', script)               # HF.init({fps, stepFps, dur})
        if m:
            for k, v in re.findall(r'(\w+)\s*:\s*([\w.\d/*+\- ]+)', m.group(1)):
                try: self.names[k] = eval(v, {'__builtins__': {}}, dict(self.names))
                except Exception: pass
            if 'dur' in self.names: self.names.setdefault('DUR', self.names['dur'])
            if self.names.get('stepFps'): self.names['SF'] = 1 / self.names['stepFps']
        self.names.setdefault('SF', self.names['F'])

    def ev(self, expr, extra=None):
        if not self.SAFE.match(expr): raise ValueError(expr)
        return float(eval(expr, {'__builtins__': {}}, dict(self.names, **(extra or {}))))


def split_args(s):
    out, depth, cur, q = [], 0, '', None
    for ch in s:
        if q:
            cur += ch
            if ch == q: q = None
            continue
        if ch in '\'"': q = ch; cur += ch; continue
        if ch in '([{': depth += 1
        if ch in ')]}': depth -= 1
        if ch == ',' and depth == 0: out.append(cur.strip()); cur = ''; continue
        cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


LOOP = re.compile(r'\[\s*(\[[^\[\]]*\](?:\s*,\s*\[[^\[\]]*\])*)\s*\]\s*\.forEach\(\s*\(\s*\[([^\]]*)\]\s*\)\s*=>\s*')


def literal(tok):
    tok = tok.strip()
    if tok[:1] in '\'"': return tok[1:-1]
    try: return float(tok)
    except ValueError: return tok


def comp_events(html, fps):
    """[(event, at_seconds, note)] from a comp's registry calls, plus ⚠ notes it could not bind."""
    script = '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', html, re.S))
    ev = Evaluator(script, fps)
    events, warns = [], []
    consumed = []                                                  # spans handled by the loop expander
    # `[[a, b, 1.1], ...].forEach(([x, y, at]) => BODY)`: bind the params per tuple, evaluate the body's calls
    for lm in LOOP.finditer(script):
        tuples = [[literal(x) for x in split_args(t[1:-1])] for t in split_args(lm.group(1))]
        params = [x.strip() for x in lm.group(2).split(',')]
        i = lm.end(); depth = 0; j = i
        if script[i] == '{':
            while j < len(script):
                depth += {'{': 1, '}': -1}.get(script[j], 0); j += 1
                if depth == 0: break
            body = script[i:j]
        else:
            while j < len(script) and script[j] not in ';\n': j += 1
            body = script[i:j]
        consumed.append((lm.start(), j))
        for tup in tuples:
            bind = {k: v for k, v in zip(params, tup)}
            for cm in re.finditer(r'\b(' + '|'.join(CALLS) + r')\(([^()]*)\)', body):
                args = split_args(cm.group(2))
                if len(args) < 2: continue
                sel = bind.get(args[0].strip(), args[0])
                try: events.append((cm.group(1), ev.ev(args[1], {k: v for k, v in bind.items() if isinstance(v, float)}), str(sel)))
                except Exception: warns.append(f'{cm.group(1)}({args[0]}, {args[1]}) in a loop could not be evaluated')
    FOR = re.compile(r'for\s*\(\s*(?:const|let|var)\s*\[([^\]]*)\]\s*of\s*(\[[^;]*?\]|\w+)\s*\)\s*')
    for fm in FOR.finditer(script):
        src = fm.group(2)
        if not src.startswith('['):                                  # `of ROWS` -> the const array literal
            cm_ = re.search(r'(?:const|let|var)\s+' + re.escape(src) + r'\s*=\s*(\[[^;]*?\])\s*;', script)
            if not cm_: warns.append(f'for-of over {src}: array not found'); continue
            src = cm_.group(1)
        tuples = [[literal(x) for x in split_args(t[1:-1])] for t in split_args(src[1:-1]) if t.startswith('[')]
        params = [x.strip() for x in fm.group(1).split(',')]
        i = fm.end(); j = i
        if script[i] == '{':
            depth = 0
            while j < len(script):
                depth += {'{': 1, '}': -1}.get(script[j], 0); j += 1
                if depth == 0: break
        else:
            while j < len(script) and script[j] not in ';\n': j += 1
        body = script[i:j]; consumed.append((fm.start(), j))
        for tup in tuples:
            bind = {k: v for k, v in zip(params, tup)}
            for cm in re.finditer(r'\b(' + '|'.join(CALLS) + r')\(([^()]*(?:\([^()]*\)[^()]*)*)\)', body):
                args = split_args(cm.group(2))
                if len(args) < 2: continue
                sel = bind.get(args[0].strip(), args[0])
                try: events.append((cm.group(1), ev.ev(args[1], {k: v for k, v in bind.items() if isinstance(v, float)}), str(sel)))
                except Exception: warns.append(f'{cm.group(1)}({args[0]}, {args[1]}) in a for-of could not be evaluated')
    # hand-rolled motion the registry would have named: a tween that carries an element a frame-width
    # in x is a slide, a stroke-dash reveal is a draw-on (pre-registry comps, and scene moves inside
    # a full-screen that no registry primitive covers)
    for fm_ in re.finditer(r'tl\.set\(([^,]+),\s*\{\s*opacity:\s*o\s*\},\s*(?:(.+?)\s*\+\s*)?f\s*\*\s*F\s*\)', script):
        try: events.append(('flash', ev.ev(fm_.group(2).strip()) if fm_.group(2) else 0.0, fm_.group(1).strip() + ' (hand-rolled strobe)'))
        except Exception:
            if not re.fullmatch(r'\w+', (fm_.group(2) or '').strip()): warns.append(f'flash {fm_.group(1).strip()} at {fm_.group(2).strip()}: could not be evaluated')
    for hm in re.finditer(r'tl\.to\(([^,]+),\s*\{([^}]*)\},\s*([^)]+)\)', script):
        props, at_expr = hm.group(2), hm.group(3).strip()
        xm = re.search(r'\bx:\s*(-?\d+(?:\.\d+)?)', props)
        kind = None
        if xm and abs(float(xm.group(1))) >= 900: kind = 'slideOut' if float(xm.group(1)) < 0 else 'slideIn'
        elif re.search(r'strokeDashoffset:\s*0\b', props): kind = 'drawOn'
        if not kind: continue
        try: events.append((kind, ev.ev(at_expr), hm.group(1).strip() + ' (hand-rolled)'))
        except Exception:
            if not re.fullmatch(r'\w+', at_expr):                    # a bare unknown name is a helper's parameter, not a call
                warns.append(f'{kind} {hm.group(1).strip()} at {at_expr}: could not be evaluated')
    for m in re.finditer(r'\b(' + '|'.join(CALLS) + r')\(', script):
        if any(a <= m.start() < b for a, b in consumed): continue
        name = m.group(1)
        i = m.end(); depth = 1; j = i
        while j < len(script) and depth:
            depth += {'(': 1, ')': -1}.get(script[j], 0); j += 1
        args = split_args(script[i:j - 1])
        if name == 'exit' and (not args or len(args) < 2):
            continue                                              # exit() at the comp end: silent anyway
        if len(args) < 2: continue
        at_expr, sel = args[1], args[0]
        extra = {}
        if 'dur' in [a.strip() for a in args[2:3]]: pass
        try:
            if re.search(r'\bi\b', at_expr):
                # a loop over an array literal just above the call: expand over its length
                before = script[max(0, m.start() - 400):m.start()]
                arr = re.findall(r'\[([^\[\]]*)\]\s*\.forEach', before)
                n = len(split_args(arr[-1])) if arr else None
                if n is None:
                    warns.append(f'{name}({sel}, {at_expr}) runs in a loop this parser cannot size')
                    continue
                for k in range(n):
                    events.append((name, ev.ev(at_expr, {'i': k}), f'{sel} [{k}]'))
            else:
                t = ev.ev(at_expr)
                dur = None
                if name == 'countUp' and len(args) > 2:
                    try: dur = ev.ev(args[2])
                    except Exception: dur = None
                if name == 'reveal' and len(args) > 2 and args[2][:1] in '\'"`':
                    # reveal(sel, at, text): the registry reveals 2-6 words per beat on a fixed burst
                    # pattern, doubling on punctuation; replay that on the literal text for the duration
                    text = args[2][1:-1]; words_ = text.split(' '); sizes = [3, 5, 2, 4, 6, 3, 2, 5, 4, 3, 6, 2]
                    beat = ev.names['SF'] if ev.names.get('stepFps') else 2 * ev.names['F']
                    i_ = 0; k_ = 0; dur = 0.0
                    while i_ < len(words_):
                        i_ = min(len(words_), i_ + sizes[k_ % len(sizes)]); k_ += 1
                        dur += 2 * beat if re.search(r'[.,;:!?]$', ' '.join(words_[:i_])) else beat
                elif name == 'reveal':
                    warns.append(f'reveal({sel}) has no literal text: give it a hand entry with dur')
                events.append((name, t, sel if dur is None else f'{sel} dur {dur:.2f}'))
                if dur is not None: events[-1] = (name, t, events[-1][2], dur)
        except Exception:
            warns.append(f'{name}({sel}, {at_expr}) could not be evaluated')
    return events, warns


def find_comp(hf, gid, render):
    """The comp behind a placed row: any hf-graphics/*/compositions/<stem>.html whose stem is the row's
    id, or prefixes the render's filename (older jobs name comps by slug: g5-oneshot-alpha-slam2.mov
    -> g5-oneshot.html). Longest stem wins so g11b beats g11."""
    comps = sorted(hf.glob('*/compositions/*.html'), key=lambda p: -len(p.stem))
    base = Path(render).stem
    for c in comps:
        if c.stem == gid or base == c.stem or base.startswith(c.stem + '-'): return c
    for c in comps:
        if c.stem.startswith(gid + '-'): return c
    return None


def text_events(html):
    """One event per word span; the word comes from data-w when the builder wrote it, else the span text."""
    out = []
    for m in re.finditer(r'<span class="(w[^"]*)" data-t="([\d.]+)"([^>]*)>([^<]*)', html):
        w = re.search(r'data-w="([^"]*)"', m.group(3))
        out.append(('word', float(m.group(2)), htmlmod.unescape((w.group(1) if w else m.group(4)).strip()), m.group(1)))
    return out


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    job = Path(a[0]).resolve(); dry = '--dry' in a
    hf = job / 'hf-graphics'
    rows_in = json.load(open(hf / 'placement.json'))
    plan = json.load(open(job / 'graphics-plan.json'))
    preset_dir = ROOT / plan.get('preset', 'presets/youtube/default')
    if preset_dir.is_file(): preset_dir = preset_dir.parent          # plans point at the style doc
    cfg = json.load(open(preset_dir / 'sfx.json'))
    lib = ROOT / cfg['library']
    fps = probe_fps(next(r['file'] for r in rows_in if os.path.exists(r['file'])))
    F = 1 / fps
    snap = lambda t: round(round(t / F) * F, 4)
    T = cfg['targets_dbfs']; TR = cfg['tracks']; EV = cfg['events']
    rot = {}
    out, warns = [], []
    seen_gids = set()
    # hand entries for comps whose motion is not written with the registry (pre-2026-09-02 jobs):
    # hf-graphics/sfx-hand.json = [{"gid", "event", "at": <comp-relative seconds>, "note"?, "dur"?}]
    HAND = {}
    hp = hf / 'sfx-hand.json'
    if hp.exists():
        for h in json.load(open(hp)): HAND.setdefault(h['gid'], []).append(h)
    # the plan cell behind a placed row (id equal, or the row id is <planid>-<slug>): its KIND decides
    # some pairings (a pop inside a list/card graphic is a row tick, not an object)
    cells = {b['id']: b for b in plan.get('beats', []) if b.get('graphic')}
    def cell_kind(gid):
        c = cells.get(gid) or next((cells[k] for k in sorted(cells, key=len, reverse=True) if gid.startswith(k + '-')), None)
        return (c or {}).get('kind', '')
    first_cut_in = True

    def add(gid, event, at, note='', dur=None, level=None, auto=True):
        spec = EV.get(event)
        if spec is None or not isinstance(spec, dict): return
        if auto and spec.get('hand_only'): return
        path = str(lib / spec['file'])
        if not os.path.exists(path): warns.append(f'{event}: {spec["file"]} missing from {lib}'); return
        k = rot.get(event, 0); rot[event] = k + 1
        s_in, s_out = (0.0, file_dur(path)) if spec.get('whole_file') else spec['slices'][k % len(spec['slices'])]
        if spec.get('fit') == 'duration' and dur: s_out = min(s_out, s_in + max(dur, 0.2))
        at = at - spec.get('lead_frames', 0) * F + spec.get('offset_frames', 0) * F
        peak = slice_peak(path, s_in, s_out)
        if peak < -40:
            warns.append(f'{event}: slice {s_in}-{s_out} of {spec["file"]} is silent ({peak} dBFS), skipped'); return
        lvl = int(round(level)) if level is not None else (spec['level_db'] if 'level_db' in spec else min(6, round(T[spec['class']] - peak)))   # hand > fixed > class band
        out.append(dict(gid=gid, event=event, at=snap(at), file=path, src_in=round(s_in, 3), src_out=round(s_out, 3),
                        level_db=lvl, cls=spec['class'], note=note, peak=peak))

    for r in sorted(rows_in, key=lambda r: r['start']):
        gid, kind, start = r['id'], r.get('kind'), float(r['start'])
        comp = find_comp(hf, gid, r['file'])
        if not comp:
            warns.append(f'{gid}: no comp found under hf-graphics/*/compositions; events for it need a hand entry'); continue
        html = comp.read_text()
        hand = HAND.get(gid, []); seen_gids.add(gid)
        drop = {d for h in hand for d in h.get('drop', [])}
        words = text_events(html)                                  # word spans: a text animation, or a line inside a full-screen
        # a hand entry addressed by WORD (any event) resolves to that span's time; emphasis also
        # takes the word's scissors away
        emph = set()
        for h in hand:
            if not h.get('word') or h.get('at') is not None: continue
            key = h['word'].lower().strip('.,!?')
            hit = next((t for _, t, w_, _ in words if w_.lower().strip('.,!?') == key), None)
            if hit is None: warns.append(f"{gid}: hand entry word {h['word']!r} matches no span in {comp.name}"); continue
            h['at'] = hit
            if h['event'] == 'emphasis': emph.add(key)
        # the text builder's ENTRANCE decides the word sound: rise -> scissors (a RED word -> the
        # Error Buzz, an EMPHASIS hand entry -> the Impact), punch/pop -> the pop, slam -> the
        # Impact stamp, flicker -> ONE Neon Flicker at the block's first word (the strobe start)
        ent = (re.search(r'const ENTRANCE\s*=\s*"(\w+)"', html) or [None, 'rise'])[1]
        if ent == 'punch':                                          # the builder emits pop AND slam as "punch"; the shape tells them apart
            over = re.search(r'POP_OVER\s*=\s*([\d.]+)', html)
            ent = 'pop' if over and float(over.group(1)) > 0 else 'slam'
        if ent == 'flicker' and words:
            add(gid, 'word-flicker', start + min(t for _, t, _, _ in words), 'flicker strobe: ' + ' '.join(w_ for _, _, w_, _ in words))
        else:
            wev = {'pop': 'word-pop', 'slam': 'word-slam'}.get(ent, 'word')
            for ev, t, w_, cls in words:
                key = w_.lower().strip('.,!?')
                if key in emph: continue                            # the emphasis hand entry places its own row
                if wev == 'word' and 'red' in cls.split() and 'word-negative' not in drop: add(gid, 'word-negative', start + t, f'{w_} (red: negation)'); continue
                if wev not in drop: add(gid, wev, start + t, f'{w_} ({ent})' if ent != 'rise' else w_)
        if kind == 'text' and words and not any(h.get('at') is not None for h in hand): continue   # a pure text animation has no other events (a hand entry keeps going)
        evs, w = comp_events(html, fps)
        ck = cell_kind(gid)
        evs = [e for e in evs if e[0] not in drop]
        if ck in ('list', 'card'): evs = [('row-tick',) + tuple(e[1:]) if e[0] == 'pop' else e for e in evs]   # rows tick on, objects pop
        hand_evs = [(h['event'], float(h['at']), h.get('note', 'hand'), h.get('dur'), h.get('level_db')) for h in hand if h.get('at') is not None]
        for h in hand_evs: evs.append(h)
        warns += [f'{gid}: {x}' for x in w if not any(x.startswith(k + '(') for k, v in EV.items() if v is None)]
        if not evs and not w and not words:
            warns.append(f'{gid}: no registry calls found in {comp.name} (hand-rolled motion): its events need a hand entry')
        if kind == 'full':
            if not any(e[0] == 'flash' and abs(e[1]) <= 2 * F + 1e-4 for e in evs) and 'cut-in' not in drop:
                add(gid, 'cut-in', start, 'hard cut into the full-screen')   # a flicker on frame 0 IS the cut's sound
            if EV.get('riser') and (first_cut_in or not EV['riser'].get('first_cut_in_only', True)):   # the riser belongs to the FIRST full-screen, whoosh or not
                sp = EV['riser']; d = sp['slices'][0][1] - sp['slices'][0][0]
                t0 = start - cfg['riser_gap_s'] - d
                if t0 >= 0: add(gid, 'riser', t0, 'first cut-in of the job')
                else: warns.append(f'{gid}: no room for the riser before the first full-screen at {start:.2f}s (needs {cfg["riser_gap_s"] + d:.2f}s)')
                first_cut_in = False
        for e in evs:
            name, t, note = e[0], e[1], e[2]
            dur = e[3] if len(e) > 3 else None
            level = e[4] if len(e) > 4 else None
            if t < 0 or t > float(r['end']) - start + 0.05: continue
            add(gid, name, start + t, note, dur, level, auto=(len(e) <= 4))

    for g_ in HAND:
        if g_ not in seen_gids: warns.append(f'sfx-hand.json names {g_!r}, which is not a placed graphic (placement.json ids: check the spelling)')
    # layer stacking: a sound that would OVERLAP a different sound already on a track goes a layer
    # down, so both ring out (the reference put Deep Whoosh 3 under Deep Whoosh 4 on its own track);
    # the same sound repeating on top of itself stays on one track and truncates, which is exactly
    # the reference's machine-gun pops (0.29 / 0.25 / 0.21s, each cut by the next). An identical
    # sound within 2 frames is a doubling, not a layer, and is dropped.
    out.sort(key=lambda x: x['at'])
    win = cfg['layer_window_frames'] * F + 1e-4
    placed = []
    final = []
    for x in out:
        near = [p for p in placed if abs(p['at'] - x['at']) <= win]
        if any(p['file'] == x['file'] for p in near): continue      # one sound per frame; a second copy is a doubling, not a layer
        x_end = x['at'] + (x['src_out'] - x['src_in'])
        used = {p['track'] for p in placed if p['file'] != x['file'] and p['at'] < x_end and x['at'] < p['at'] + (p['src_out'] - p['src_in'])}
        for tr in (TR['primary'], TR['layer2'], TR['layer3']):
            if tr not in used: x['track'] = tr; break
        else:
            warns.append(f"{x['gid']} {x['event']} @{x['at']}: four sounds on one frame, dropped"); continue
        placed.append(x); final.append(x)
    for i, x in enumerate(final): x['id'] = f's{i + 1:03d}'

    # cut sheet
    span = (final[-1]['at'] - final[0]['at']) if len(final) > 1 else 0
    lines = [f"# SFX plan — {job.name}", '',
             f"{len(final)} sounds over {span:.1f}s ({len(final) / span if span else 0:.2f}/s) · preset {preset_dir.relative_to(ROOT)} · fps {fps:.3f}", '',
             '| # | at | track | graphic | event | sound | slice | level | peak→ | note |', '|---|---|---|---|---|---|---|---|---|---|']
    for x in final:
        lines.append(f"| {x['id']} | {x['at']:.3f} | A{x['track'] + 1} | {x['gid']} | {x['event']} | {os.path.basename(x['file'])} | "
                     f"{x['src_in']:.2f}–{x['src_out']:.2f} | {x['level_db']:+d} dB | {x['peak'] + x['level_db']:.1f} | {x['note']} |")
    if warns:
        lines += ['', '## ⚠ needs a hand entry', ''] + [f'- {w}' for w in warns]
    md = '\n'.join(lines) + '\n'
    if dry:
        print(md); return
    json.dump(final, open(hf / 'sfx-plan.json', 'w'), indent=1)
    (hf / 'sfx-plan.md').write_text(md)
    print(f"wrote {len(final)} rows -> {hf / 'sfx-plan.json'} (+ sfx-plan.md); {len(warns)} ⚠")
    for w in warns: print('  ⚠ ' + w)


if __name__ == '__main__':
    main()
