#!/usr/bin/env python3
"""polish-boundaries.py — uniform, peak-relative cut boundaries for every segment.

Built 2026-08-28 from the your-job session, where you heard exactly what the
old absolute-threshold measurement produces: some words clipped at the end, others with
too much room ("you're not even cutting right at the end of some words"). Hardened the
same day by an adversarial review (10 findings, all fixed here). Root causes covered:

  1. A threshold set from the noise floor alone falls below room tone on quiet setups,
     so a "decay" walks seconds into the gap and the clamp then cuts the word short.
  2. A soft voiced decay drops below an absolute threshold while still audible.
  3. A breath after a word gets counted as part of it (out lands late).
  4. Low-probability boundary words (p <= 0.35 clusters) mean the WhisperX TIMESTAMP IS
     FICTION, not just soft — real speech ran ~750 ms past the claimed end on a measured
     case ("...90% of the way th—"). That applies to the NEXT word too: a low-prob next
     word makes the search limit itself fiction, so the limit extends to the next
     TRUSTED word.
  5. refine-cuts.py classifies a dead-air kill between ADJACENT transcript words as a
     continuous split: it skips measuring those boundaries entirely.
  6. The two sides of a joint must be resolved as a PAIR (same invariant as refine's
     pass 3): independent measurement can cross in the shared silence and play frames
     twice. A pairwise pass runs after measurement; continuous splits butt-join exactly.

Method (validated on your-job v2.1):
  envelope     5 ms RMS in dB; LOCAL noise floor = 10th pct of a −2s..+2.5s window
  threshold    max(floor + 10 dB, word peak − 28 dB)
  OUT          decay end (sustained 100 ms quiet terminator), hard-capped at
               word.end + 300 ms — widened past low-prob words to the next trusted one
               out = decay + 70 ms, uniform on every segment (authored per-segment
               "air" was retired 2026-08-31 — see SKILL.md; tails never vary)
  IN           onset (40 ms of quiet required before it) − 40 ms
  joints       resolved pairwise after measurement; a continuous split (adjacent kept
               words) shares ONE boundary in the inter-word gap; real-cut overlaps are
               split at the midpoint; a pinned side never moves
  pins         segments arriving with no_refine are LEFT UNTOUCHED (hand-pins survive,
               and the step is idempotent); everything is pinned on output
  long-span    a merged-repeat word (> 1.0 s) at an OUT cuts after its FIRST utterance;
               at an IN the upstream prefer-last snap is kept as authored
  ⚠ lines      no-decay against a killed region, killed-neighbor grafts, long-spans,
               hot cuts — each one is a clipped word / flubbed take candidate: verify
               by slice re-ASR (SKILL.md Step 3.8), never ship unheard

Usage (after splice.sh's refine pass has produced cuts.refined.json):
  python3 polish-boundaries.py <job_dir>
Reads  /tmp/video-editor/<job>/cuts.refined.json (falls back to transcript/cuts.json)
Writes /tmp/video-editor/<job>/cuts.json with every segment pinned, and deletes
cuts.refined.json/cuts.snapped.json so the next splice.sh run consumes the pinned EDL.
Re-run splice.sh after this (RENDER=0 on the FIRST splice of any lane — the render
belongs after this step).
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import wave
import array

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

HOP_S = 0.005
TAIL_S = 0.07          # uniform out tail past the measured decay
LEAD_S = 0.04          # uniform in lead before the measured onset
DECAY_CAP_S = 0.30     # max decay length past the claimed word end (breath guard)
LOWPROB = 0.35         # words at/below this probability: timestamp is untrusted
QUIET_TERM_S = 0.10    # sustained quiet that ends a decay
ONSET_QUIET_S = 0.04   # quiet required immediately before an onset
JOINT_GAP_S = 0.20     # max authored gap for two segments to count as one joint
LONG_SPAN_S = 1.0      # merged-repeat word span threshold


def die(msg):
    print(f"[polish] {msg}", file=sys.stderr)
    sys.exit(1)


def decode_mono16k(path):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
         "-y", tmp.name],
        capture_output=True)
    if r.returncode != 0:
        die(f"ffmpeg decode failed for {path}: {r.stderr.decode()[:300]}")
    wf = wave.open(tmp.name, "rb")
    sr = wf.getframerate()
    pcm = array.array("h")
    pcm.frombytes(wf.readframes(wf.getnframes()))
    wf.close()
    os.unlink(tmp.name)
    return pcm, sr


class Env:
    def __init__(self, pcm, sr):
        self.hop = max(1, int(sr * HOP_S))
        self.sr = sr
        self.db = []
        for i in range(0, len(pcm) - self.hop, self.hop):
            seg = pcm[i:i + self.hop]
            r = math.sqrt(sum(x * x for x in seg) / len(seg))
            self.db.append(20 * math.log10(r + 1.0))

    def idx(self, t):
        return max(0, min(len(self.db) - 1, int(t * self.sr / self.hop)))

    def t(self, k):
        return k * self.hop / self.sr

    def floor(self, t):
        w = self.db[self.idx(t - 2.0):self.idx(t + 2.5)]
        return sorted(w)[len(w) // 10] if w else 25.0

    def band(self, t0, t1):
        w = self.db[self.idx(t0):self.idx(t1)]
        return sum(w) / len(w) if w else 0.0


def main():
    if len(sys.argv) < 2:
        die("usage: polish-boundaries.py <job_dir>")
    job_dir = os.path.abspath(sys.argv[1])
    job = os.path.basename(job_dir)
    tmpdir = f"/tmp/video-editor/{job}"
    src = os.path.join(tmpdir, "cuts.refined.json")
    if not os.path.exists(src):
        src = os.path.join(job_dir, "transcript", "cuts.json")
    if not os.path.exists(src):
        die(f"no cuts found ({tmpdir}/cuts.refined.json or transcript/cuts.json)")
    # The refined EDL is a splice by-product. If the AUTHORED EDL (the /tmp cuts.json splice
    # reads, or the persisted transcript/cuts.json) is newer than it, the refine is stale and
    # this pass would polish the PRE-EDIT cut and report every segment "hand-pinned, untouched"
    # (your-job 2026-09-02: it did exactly that against an EDL edited a minute earlier).
    # The right order is: edit cuts.json -> splice.sh -> polish-boundaries.py -> splice.sh.
    if src.endswith("cuts.refined.json"):
        for authored in (os.path.join(tmpdir, "cuts.json"),
                         os.path.join(job_dir, "transcript", "cuts.json")):
            if os.path.exists(authored) and os.path.getmtime(authored) > os.path.getmtime(src) + 0.5:
                die(f"{authored} is NEWER than {src}: the refined EDL is stale.\n"
                    f"  Re-run splice.sh (RENDER=0 is fine) so refine-cuts measures the edited EDL, "
                    f"then polish.")
    print(f"[polish] source: {src}")
    cuts = json.load(open(src))
    words_doc = json.load(open(os.path.join(job_dir, "transcript", "words.json")))
    clips = {os.path.basename(c["clip"]): c for c in words_doc["clips"]}
    segs = cuts["segments"]
    for s in segs:
        if os.path.basename(s["clip"]) not in clips:
            die(f"clip {s['clip']!r} not in words.json")

    used = {os.path.basename(s["clip"]) for s in segs}
    envs = {}
    for name in used:
        c = clips[name]
        raw = c.get("path") or os.path.join(job_dir, "raw", name)
        if not os.path.exists(raw):
            raw = os.path.join(job_dir, "raw", name)
        pcm, sr = decode_mono16k(raw)
        envs[name] = Env(pcm, sr)

    warns = []
    meta = []          # per-segment: dict(clip, i_first, i_last, pinned, orig_a, orig_b)

    # ---------------- pass 1: per-segment measurement ----------------
    for i, s in enumerate(segs):
        clip = os.path.basename(s["clip"])
        wd = clips[clip]["words"]
        env = envs[clip]
        a, b = float(s["start"]), float(s["end"])
        pinned = bool(s.get("no_refine"))
        # membership by OVERLAP (refine's own rule): the words this segment plays
        overl = [(k, w) for k, w in enumerate(wd) if w["end"] > a and w["start"] < b]
        m = dict(clip=clip, orig_a=a, orig_b=b, pinned=pinned,
                 i_first=overl[0][0] if overl else None,
                 i_last=overl[-1][0] if overl else None,
                 butt_in=False, butt_out=False)
        meta.append(m)
        if pinned:
            print(f"seg{i:>3} (hand-pinned — untouched)")
            continue
        if not overl:
            warns.append(f"seg{i}: wordless — boundaries kept as authored")
            continue
        wa = overl[0][1]
        wb = overl[-1][1]
        pw = wd[m["i_first"] - 1] if m["i_first"] > 0 else None
        nw = wd[m["i_last"] + 1] if m["i_last"] + 1 < len(wd) else None

        # joint tests use AUTHORED values (source-ordered, small gap)
        def joint_prev():
            if i == 0 or os.path.basename(segs[i - 1]["clip"]) != clip:
                return False
            g = a - float(meta[i - 1]["orig_b"])
            # negative gap = authored pads overlapping (the classic padded continuous
            # split) — that IS a joint; require source order, bound the overlap
            return -0.5 < g < JOINT_GAP_S and a > float(meta[i - 1]["orig_a"])

        def contiguous_prev():
            return joint_prev() and meta[i - 1]["i_last"] is not None and \
                m["i_first"] <= meta[i - 1]["i_last"] + 1

        # ---------------- IN ----------------
        in_note = "kept"
        if (wa["end"] - wa["start"]) > LONG_SPAN_S and a > wa["start"] + 0.05:
            # merged-repeat start: the upstream prefer-last-take snap put the cut
            # deliberately inside the word — keep it, flag for the second pass
            in_note = "long-span(prefer-last, kept)"
            warns.append(f"seg{i} IN: starts inside long-span '{wa['w']}' — "
                         f"prefer-last snap kept as authored; verify by ear/slice-ASR")
        else:
            fl = env.floor(wa["start"])
            peak = max(env.db[env.idx(wa["start"] - 0.05):
                              env.idx(wa["start"] + 0.25) + 1] or [fl])
            thr = max(fl + 10.0, peak - 28.0)
            lo = max((pw["end"] - 0.02) if pw else 0.0, wa["start"] - 0.25, 0.0)
            onset = None
            for k in range(env.idx(lo), env.idx(wa["start"] + 0.15) + 1):
                if env.db[k] >= thr:
                    qk = env.idx(env.t(k) - ONSET_QUIET_S)
                    if k > qk and all(env.db[j] < thr for j in range(qk, k)):
                        onset = env.t(k)
                        break
            if onset is not None:
                s["start"] = round(max(onset - LEAD_S,
                                       (pw["end"] - 0.01) if pw else 0.0), 3)
                in_note = f"onset−{int(LEAD_S*1000)}ms"
            elif contiguous_prev():
                m["butt_in"] = True          # resolved in the pairwise pass
                in_note = "butt-join(pending)"
            else:
                if pw is not None:
                    s["start"] = round(max(float(s["start"]), pw["end"] - 0.005,
                                           wa["start"] - 0.03), 3)
                in_note = "graft"
                warns.append(
                    f"seg{i} IN: no clean onset for '{wa['w']}' and the previous raw "
                    f"word '{pw['w'] if pw else '?'}' is KILLED — verify by ear / "
                    f"slice-ASR (possible flubbed take)")

        # ---------------- OUT ----------------
        def joint_next():
            if i + 1 >= len(segs) or os.path.basename(segs[i + 1]["clip"]) != clip:
                return False
            g = float(segs[i + 1]["start"]) - b
            return -0.5 < g < JOINT_GAP_S and float(segs[i + 1]["start"]) > a

        def contiguous_next():
            # next segment's meta isn't built yet — compute its first word directly
            if not joint_next():
                return False
            na = float(segs[i + 1]["start"])
            nb = float(segs[i + 1]["end"])
            novl = [k for k, w in enumerate(wd) if w["end"] > na and w["start"] < nb]
            return bool(novl) and novl[0] <= m["i_last"] + 1

        cont_next = contiguous_next()
        # a low-prob NEXT word makes the limit itself fiction: extend to the next
        # trusted word
        nw_trusted = nw
        kk = m["i_last"] + 1
        while nw_trusted is not None and nw_trusted.get("prob", 1.0) <= LOWPROB:
            kk += 1
            nw_trusted = wd[kk] if kk < len(wd) else None
        lowprob = wb.get("prob", 1.0) <= LOWPROB or \
            (pw is not None and m["i_last"] == m["i_first"] and
             pw.get("prob", 1.0) <= LOWPROB) or \
            (m["i_last"] > 0 and wd[m["i_last"] - 1].get("prob", 1.0) <= LOWPROB) or \
            (nw is not None and nw.get("prob", 1.0) <= LOWPROB)
        if nw is None:
            limit = b + 0.5
        elif lowprob and nw_trusted is not None and nw_trusted is not nw:
            limit = nw_trusted["start"] - 0.015
        else:
            limit = nw["start"] - 0.015

        fl = env.floor(wb["end"])
        k0 = env.idx(wb["start"])
        k1 = env.idx(min(wb["end"] + 0.06, limit))
        peak = max(env.db[k0:k1 + 1] or [fl])
        thr = max(fl + 10.0, peak - 28.0)
        out_note = "kept"
        decay = None
        if (wb["end"] - wb["start"]) > LONG_SPAN_S:
            # merged repeat at an OUT: cut after the FIRST utterance
            bursts = []
            cur = None
            for k in range(env.idx(wb["start"]),
                           env.idx(min(wb["end"] + 0.5, limit))):
                if env.db[k] >= thr:
                    if cur is None:
                        cur = [env.t(k), env.t(k)]
                    else:
                        cur[1] = env.t(k)
                elif cur and env.t(k) - cur[1] > 0.12:
                    bursts.append(tuple(cur))
                    cur = None
            if cur:
                bursts.append(tuple(cur))
            if bursts:
                decay = bursts[0][1] + HOP_S
                warns.append(f"seg{i} OUT: long-span '{wb['w']}' — cut after FIRST "
                             f"utterance @{decay:.2f}; verify (merged-repeat rule)")
        else:
            cap = limit if lowprob else min(wb["end"] + DECAY_CAP_S, limit)
            klim = env.idx(cap)
            last_above = None
            k = k0
            while k <= klim:
                if env.db[k] >= thr:
                    last_above = k
                elif last_above is not None and \
                        env.t(k) - env.t(last_above) > QUIET_TERM_S:
                    break
                k += 1
            decay = env.t(last_above) + HOP_S if last_above is not None else None
            if decay is not None:
                kq1 = env.idx(min(decay + QUIET_TERM_S, limit))
                if any(env.db[j] >= thr
                       for j in range(env.idx(decay) + 1, kq1)) and \
                        env.t(kq1) - decay >= 0.08:
                    decay = None

        if decay is not None:
            new_out = round(min(decay + TAIL_S, limit), 3)
            if new_out > float(s["start"]) + 0.1:
                s["end"] = new_out
                applied = new_out - decay
                out_note = f"decay+{int(applied*1000)}ms"
        elif cont_next:
            m["butt_out"] = True             # resolved in the pairwise pass
            out_note = "butt-join(pending)"
        else:
            out_note = "⚠ NO-DECAY"
            warns.append(
                f"seg{i} OUT: no decay found for '{wb['w']}'"
                f"{' [LOW-PROB]' if lowprob else ''} and the next raw word is KILLED "
                f"— speech may run through the cut; widen by ear or slice-ASR. "
                f"Boundary kept as authored, do NOT ship unverified.")

        # degenerate guard: never write an inverted/collapsed segment
        if float(s["end"]) <= float(s["start"]) + 0.05:
            s["start"], s["end"] = m["orig_a"], m["orig_b"]
            warns.append(f"seg{i}: measurement collapsed the segment — authored "
                         f"boundaries restored; re-author this pair")
            in_note += "/restored"
            out_note += "/restored"
        print(f"seg{i:>3} …{wb['w'][:14]:<14} in:{in_note:<26} out:{out_note}")

    # ---------------- pass 2: pairwise joint resolution ----------------
    # Same invariant as refine-cuts.py pass 3: consecutive same-clip source-ordered
    # segments may never overlap, and a continuous split shares ONE boundary.
    for i in range(len(segs) - 1):
        x, y = segs[i], segs[i + 1]
        mx, my = meta[i], meta[i + 1]
        if mx["clip"] != my["clip"]:
            continue
        gap = my["orig_a"] - mx["orig_b"]
        if not (-0.5 < gap < JOINT_GAP_S) or my["orig_a"] <= mx["orig_a"]:
            continue                       # not one joint (dead-air kill or reuse)
        wd = clips[mx["clip"]]["words"]
        contiguous = mx["i_last"] is not None and my["i_first"] is not None and \
            my["i_first"] <= mx["i_last"] + 1
        xb, ya = float(x["end"]), float(y["start"])
        if contiguous and (mx["butt_out"] or my["butt_in"] or ya < xb):
            # one unbroken take split for the timeline: ONE shared boundary, placed
            # in the inter-word gap near the midpoint
            if mx["pinned"] and my["pinned"]:
                continue
            if mx["pinned"]:
                shared = xb
            elif my["pinned"]:
                shared = ya
            else:
                # place the shared boundary in an inter-word gap BY TIME, never by
                # index — an out-pad overshoot makes the index unreliable (it made
                # seg i look like it keeps the next word), same rule as refine's
                # pass 3
                mid = (xb + ya) / 2
                k = max((j for j in range(len(wd) - 1) if wd[j]["end"] <= mid),
                        default=None)
                shared = mid if k is None else \
                    min(max(mid, wd[k]["end"]), wd[k + 1]["start"])
            x["end"] = y["start"] = round(shared, 3)
            print(f"[joint] seg{i}/{i+1}: continuous split — shared boundary "
                  f"@{shared:.3f}")
        elif ya < xb:
            # real cut whose measured edges crossed in the shared silence
            if mx["pinned"] and my["pinned"]:
                warns.append(f"seg{i}/{i+1}: OVERLAP {int((xb-ya)*1000)}ms but both "
                             f"pinned — re-author one side (splice will abort)")
            elif mx["pinned"]:
                y["start"] = x["end"]
            elif my["pinned"]:
                x["end"] = y["start"]
            else:
                mid = round((xb + ya) / 2, 3)
                x["end"] = y["start"] = mid
                print(f"[joint] seg{i}/{i+1}: OVERLAP {int((xb-ya)*1000)}ms — "
                      f"butt-joined @{mid:.3f}")

    # ---------------- hot-cut QA sweep ----------------
    for i, s in enumerate(segs):
        m = meta[i]
        if m["i_last"] is None:
            continue
        wd = clips[m["clip"]]["words"]
        env = envs[m["clip"]]
        b = float(s["end"])
        # skip resolved butt joints (the next segment resumes exactly here)
        if i + 1 < len(segs) and abs(float(segs[i + 1]["start"]) - b) < 0.002 and \
                meta[i + 1]["clip"] == m["clip"]:
            continue
        # window ends at the next TRUSTED word (a low-prob next word's start is
        # fiction and must not shield the sweep)
        kk = m["i_last"] + 1
        while kk < len(wd) and wd[kk].get("prob", 1.0) <= LOWPROB:
            kk += 1
        hi = min(b + 0.15, (wd[kk]["start"] - 0.01) if kk < len(wd) else b + 0.15)
        if hi - b < 0.04:
            continue
        fl = env.floor(b)
        if env.band(b + 0.01, hi) > fl + 12:
            warns.append(f"seg{i} OUT @{b:.2f}: speech energy past the cut — "
                         f"possible clipped tail (verify; may be the next killed "
                         f"word only if it sits closer than the trusted window)")

    for s in segs:
        s["no_refine"] = True
    for w in warns:
        print(f"⚠ {w}")
    dur = sum(float(s["end"]) - float(s["start"]) for s in segs)
    os.makedirs(tmpdir, exist_ok=True)
    json.dump(cuts, open(os.path.join(tmpdir, "cuts.json"), "w"), indent=1)
    for f in ("cuts.refined.json", "cuts.snapped.json"):
        p = os.path.join(tmpdir, f)
        if os.path.exists(p):
            os.remove(p)
    print(f"[polish] {len(segs)} segments pinned, runtime {dur:.1f}s "
          f"({dur/60:.2f} min), {len(warns)} ⚠ — wrote {tmpdir}/cuts.json; "
          f"re-run splice.sh to consume it")


if __name__ == "__main__":
    main()
