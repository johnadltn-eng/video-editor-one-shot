#!/usr/bin/env python3
"""voice-gain.py: the step-3 gain, MEASURED from the kept speech (universal, every lane).

  uv run workflows/voice-gain.py projects/<job>            # prints the measurement + the gain to use
  uv run workflows/voice-gain.py projects/<job> --json     # {"gain_db", "lufs", "true_peak", "lra", ...}

The house chain is static: +GAIN dB into a hard limiter at -6 dBFS, never dynamic. The limiter
is FIXED; the gain is whatever puts the raw's kept speech on the house target, so a quiet shoot
and a hot shoot both land in the same place (2026-09-03: "measure the raw and get it to
where +15 put your-job"). The target was locked on that job: its kept speech measured
-32.1 LUFS integrated and +15 dB was perfect, so

    TARGET = -17 LUFS integrated, pre-limiter    ->    gain = round(TARGET - measured)

That is deliberately hot: the true peak lands well above the -6 ceiling and the limiter works on
every stressed syllable, which is the saturation he likes. Measured on the KEPT ranges only
(transcript/cuts.json against raw/), never the whole take: dead air and the slate would drag the
integrated number down and over-gain the speech.
"""
import json, os, re, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # Windows pipes default to cp1252, which cannot encode the status glyphs
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

TARGET_LUFS = -17.0
LIMIT_DBFS = -6.0
GAIN_MIN, GAIN_MAX = 0, 24


def measure(raw, ranges):
    sel = '+'.join(f'between(t,{a:.4f},{b:.4f})' for a, b in ranges)
    af = f"aselect='{sel}',asetpts=N/SR/TB,ebur128=peak=true:framelog=quiet,volumedetect"
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', raw, '-af', af, '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    g = lambda pat: float(re.search(pat, r).group(1))
    return dict(lufs=g(r'I:\s+(-?[\d.]+) LUFS'), lra=g(r'LRA:\s+([\d.]+) LU'),
                true_peak=g(r'Peak:\s+(-?[\d.]+) dBFS'), mean=g(r'mean_volume: (-?[\d.]+)'), kept_s=sum(b - a for a, b in ranges))


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    job = Path(a[0]).resolve()
    cuts = json.load(open(job / 'transcript' / 'cuts.json'))['segments']
    by_clip = {}
    for s in cuts:
        by_clip.setdefault(os.path.basename(s.get('clip') or ''), []).append((float(s['start']), float(s['end'])))
    raws = sorted(job.glob('raw/*'))
    out = []
    for clip, ranges in by_clip.items():
        raw = next((p for p in raws if p.name == clip), None) or (raws[0] if len(raws) == 1 else None)
        if not raw: sys.exit(f'no raw file for {clip!r} under {job / "raw"}')
        m = measure(str(raw), ranges); m['raw'] = raw.name; out.append(m)
    # one gain for the whole job: weight the per-clip integrated loudness by kept seconds
    tot = sum(m['kept_s'] for m in out)
    lufs = sum(m['lufs'] * m['kept_s'] for m in out) / tot
    tp = max(m['true_peak'] for m in out)
    gain = int(round(TARGET_LUFS - lufs))
    warn = None
    if gain < GAIN_MIN or gain > GAIN_MAX:
        warn = f'gain {gain:+d} is outside {GAIN_MIN}..{GAIN_MAX}: the raw is far off a normal shoot, check it before trusting this'
        gain = max(GAIN_MIN, min(GAIN_MAX, gain))
    res = dict(gain_db=gain, target_lufs=TARGET_LUFS, lufs=round(lufs, 1), true_peak=tp, lra=out[0]['lra'],
               over_ceiling_db=round(tp + gain - LIMIT_DBFS, 1), kept_s=round(tot, 1), clips=out, warn=warn,
               premiere_amplify_v=round((gain + 96) / 144, 6))
    if '--json' in a:
        print(json.dumps(res)); return
    print(f"kept speech {res['kept_s']}s in {len(out)} clip(s): {res['lufs']} LUFS integrated · true peak {tp} dBFS · LRA {res['lra']} LU")
    print(f"target {TARGET_LUFS} LUFS pre-limiter -> gain {gain:+d} dB  (Amplify v={res['premiere_amplify_v']}; limiter stays at {LIMIT_DBFS:.0f} dBFS, peaks land {res['over_ceiling_db']:+.1f} dB over it)")
    if warn: print('⚠ ' + warn)


if __name__ == '__main__':
    main()
