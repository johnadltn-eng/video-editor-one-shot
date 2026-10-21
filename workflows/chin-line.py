# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless"]
# ///
"""
chin-line.py — measure the chin line of a talking-head cut. Measured, not guessed.

Every overlay that shares the frame with the face lives BELOW the chin, and the
only honest way to know where the chin is is to look. This sweeps the video,
detects the face on each sample (OpenCV YuNet, model vendored in assets/models/)
and reports the LOWEST jaw line it finds — the worst case a fixed layout band has
to clear. The YuNet box bottom sits on the jaw, so it is the chin proxy.

Feeds the youtube/default text-animation band (presets/youtube/default/text-animation/build.py
TOP_MIN) and any hand-authored overlay that has to sit under the face. Re-derive
per shoot: a tighter or wider frame moves the chin by 100px+.

Usage:
  uv run workflows/chin-line.py projects/<job>/outputs/<job>.mp4
  uv run workflows/chin-line.py <video> --from 43.3 --to 47.0   # one graphic's window
  uv run workflows/chin-line.py <video> --json                  # machine-readable
  uv run workflows/chin-line.py <video> --annotate out.png      # eyeball the worst frame
"""
import argparse, json, os, statistics, subprocess, sys, tempfile

# Windows consoles/pipes default to cp1252 and cannot encode the status glyphs below.
for _s in (sys.stdout, sys.stderr):
    try:
        if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(REPO, "assets", "models", "face_detection_yunet_2023mar.onnx")
GAP = 70          # the breathing room a layout band leaves under the worst chin
STEP = 0.5        # sweep interval, seconds


def probe(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,duration", "-of", "csv=p=0", video],
        capture_output=True, text=True, check=True).stdout
    # iPhone side-data streams make the csv writer emit extra elements — keep the reals.
    out = [t for t in out.strip().splitlines()[0].split(",") if t.strip()]
    return int(out[0]), int(out[1]), float(out[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--step", type=float, default=STEP)
    ap.add_argument("--gap", type=float, default=GAP)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--annotate", metavar="OUT.PNG")
    a = ap.parse_args()

    import cv2
    w, h, dur = probe(a.video)
    t1 = a.t1 if a.t1 is not None else dur
    det = cv2.FaceDetectorYN.create(MODEL, "", (w, h), 0.6, 0.3, 5000)
    det.setInputSize((w, h))

    td = tempfile.mkdtemp()
    frame = os.path.join(td, "f.png")
    hits, misses, t = [], 0, a.t0 + 0.3
    while t < t1:
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", a.video,
                        "-frames:v", "1", "-y", frame], check=True)
        img = cv2.imread(frame)
        _, faces = det.detect(img)
        if faces is None:
            misses += 1
        else:
            f = faces[0]
            hits.append((round(float(f[1] + f[3])), round(t, 2)))
        t += a.step

    if not hits:
        sys.exit("no face detected anywhere in the window — measure by hand")

    hits.sort(reverse=True)
    lowest, at = hits[0]
    med = statistics.median([v for v, _ in hits])
    floor = round(lowest + a.gap)

    if a.annotate:
        subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{at}", "-i", a.video,
                        "-frames:v", "1", "-y", frame], check=True)
        img = cv2.imread(frame)
        cv2.line(img, (0, lowest), (w, lowest), (0, 0, 255), 3)
        cv2.line(img, (0, floor), (w, floor), (0, 255, 0), 3)
        cv2.putText(img, f"chin {lowest}", (24, lowest - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)
        cv2.putText(img, f"floor {floor}", (24, floor - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3)
        cv2.imwrite(a.annotate, img)

    if a.json:
        print(json.dumps({"lowest_chin": lowest, "at": at, "median_chin": med,
                          "floor": floor, "gap": a.gap, "samples": len(hits),
                          "misses": misses, "frame": [w, h]}, indent=2))
        return
    print(f"samples {len(hits)} (+{misses} no-face)   frame {w}x{h}")
    print(f"median chin  y{med:.0f}")
    print(f"LOWEST chin  y{lowest}  at t={at}s   ← the worst case a band must clear")
    print(f"→ overlay floor  y{floor}  (chin + {a.gap:.0f}px)")
    if a.annotate:
        print(f"  annotated worst frame: {a.annotate}")


if __name__ == "__main__":
    main()
