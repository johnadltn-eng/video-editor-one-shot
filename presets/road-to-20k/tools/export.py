#!/usr/bin/env python3
"""Road to 20K: export the job's sequence to the 4-final folder at -14 LUFS integrated, true peak under -1 dBTP.

  python3 presets/road-to-20k/tools/export.py <job> [--out /path/final.mp4] [--lufs -14] [--tp -1.0]

Default out: ~/Movies/Road to 20K/Day NNN/4-final/<job>-final.mp4 (NNN from the job name day-NNN-road-to-20k).
The proven route (Days 1-7): Premiere renders it (exportAsMediaDirect, NEVER Adobe Media Encoder), started in the
background and polled, because a foreground call can be cancelled mid-render and leave a truncated file
-> a WAV bounce of the same mix -> ffmpeg static gain to the target + 4x oversampled limiter at -2.0 dBFS -> AAC 192k,
video stream-copied -> measured. (Grafting Loudness Normalization into the .epr makes Premiere throw: don't.)
Stops with an error instead of writing a file that misses the spec.
"""
import json, re, subprocess, sys, time, glob
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bridge import es, job_dir, ACTIVATE, REPO, BRIDGE

a = sys.argv[1:]
if not a: sys.exit(__doc__)
job = job_dir(a[0])
arg = lambda k, d: a[a.index(k) + 1] if k in a else d
LUFS, TP = float(arg("--lufs", -14)), float(arg("--tp", -1.0))
m = re.match(r"day-(\d+)-", job.name)
out = Path(arg("--out", str(Path.home() / "Movies/Road to 20K" / f"Day {m.group(1)}" / "4-final" / f"{job.name}-final.mp4") if m else ""))
if not str(out): sys.exit("pass --out (job name is not day-NNN-road-to-20k)")
out.parent.mkdir(parents=True, exist_ok=True)
work = job / "outputs" / "export"; work.mkdir(parents=True, exist_ok=True)
proj = job / "premiere" / f"{job.name}.prproj"
EPR = Path(__file__).resolve().parents[1] / "export" / "h264-cbr50-aac192.epr"
ver = es('(function(){ return "OK:" + app.version; })()')
year = 2000 + int(str(ver).split(".")[0])
wavs = glob.glob(f"/Applications/Adobe Premiere Pro {year}/*.app/Contents/MediaIO/systempresets/*/Waveform Audio 48kHz 16-bit.epr") \
    or glob.glob("/Applications/Adobe Premiere Pro */*.app/Contents/MediaIO/systempresets/*/Waveform Audio 48kHz 16-bit.epr")
if not wavs: sys.exit("no 'Waveform Audio 48kHz 16-bit.epr' system preset found")
WAV_EPR = wavs[0]
dur = float(es(r"""(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
  var s = app.project.activeSequence; app.project.save(); return "OK:" + (s.end / 254016000000); })()""" % (json.dumps(str(proj)), json.dumps(job.name))))
print(f"Premiere {ver} · sequence {dur:.3f}s")


def probe_dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except ValueError: return 0.0


def render(dst, preset):
    if dst.exists(): dst.unlink()
    js = r"""(function(){ /*ACTIVATE*/ var e = __activate(%s, %s); if (e) return e;
      app.project.activeSequence.exportAsMediaDirect(%s, %s, app.encoder.ENCODE_ENTIRE); return "OK:done"; })()""" % (
        json.dumps(str(proj)), json.dumps(job.name), json.dumps(str(dst)), json.dumps(str(preset)))
    js = js.replace("/*ACTIVATE*/", ACTIVATE)
    p = subprocess.Popen(["node", str(BRIDGE), "execute_extendscript", json.dumps({"script": js})],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=REPO)   # background: never block on the render
    t0, last, stable = time.time(), -1, 0
    while time.time() - t0 < 1800:
        time.sleep(3)
        size = dst.stat().st_size if dst.exists() else 0
        stable = stable + 1 if size and size == last else 0
        last = size
        if stable >= 3 and abs(probe_dur(dst) - dur) < 0.1:
            p.poll(); print(f"  rendered {dst.name} ({size / 1e6:.1f} MB, {probe_dur(dst):.3f}s)"); return
    sys.exit(f"render did not finish cleanly: {dst} (duration {probe_dur(dst):.3f}s vs {dur:.3f}s)")


def measure(p):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1)), float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", s).group(1))


vid, wav = work / f"{job.name}-premiere.mp4", work / f"{job.name}-mix.wav"
print("1/4 video render (Premiere, background)"); render(vid, EPR)
print("2/4 WAV bounce of the mix"); render(wav, WAV_EPR)
i0, _ = measure(wav)
gain = LUFS - i0
print(f"3/4 mix {i0:.1f} LUFS -> static gain {gain:+.2f} dB, limiter -2.0 dBFS (4x oversampled)")
lim = 10 ** (-2.0 / 20)
tmp = work / f"{job.name}-final.tmp.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(vid), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-af", f"aresample=192000,volume={gain:.3f}dB,alimiter=limit={lim:.4f}:attack=5:release=60:level=0:asc=0,aresample=48000",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)], check=True)
i1, tp = measure(tmp)
print(f"4/4 final {i1:.1f} LUFS, true peak {tp:.1f} dBTP, {probe_dur(tmp):.3f}s")
if abs(i1 - LUFS) > 0.5 or tp > TP:
    sys.exit(f"MISSES SPEC (target {LUFS} LUFS / TP <= {TP}): kept {tmp}, nothing written to {out}")
tmp.replace(out)
print(f"-> {out}")
