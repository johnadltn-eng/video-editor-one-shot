"""Tiny helper: run ExtendScript in Premiere through lanes/premiere/premiere-bridge.mjs and get the result back.

Scripts should `return "OK:" + ...` (a plain string): the bridge JSON-parses results that look like JSON,
so a leading "OK:" keeps the payload a string. es() strips it and raises on "ERROR".
"""
import json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BRIDGE = REPO / "lanes/premiere/premiere-bridge.mjs"


def es(script: str) -> str:
    script = script.replace("/*ACTIVATE*/", ACTIVATE)
    r = subprocess.run(["node", str(BRIDGE), "execute_extendscript", json.dumps({"script": script})],
                       capture_output=True, text=True, cwd=REPO)
    out = r.stdout
    lines = [l for l in out.splitlines() if l.startswith('"')]
    if not lines:
        raise SystemExit(f"bridge: no result\n{out[-1500:]}\n{r.stderr[-800:]}")
    res = json.loads(lines[-1])
    if isinstance(res, str) and res.startswith("ERROR"):
        raise SystemExit(f"bridge: {res}")
    return res[3:] if isinstance(res, str) and res.startswith("OK:") else res


def job_dir(arg: str) -> Path:
    p = Path(arg)
    if not p.is_absolute():
        p = (REPO / "projects" / arg) if not (Path.cwd() / arg).exists() else (Path.cwd() / arg)
    if not (p / "raw").is_dir():
        sys.exit(f"not a job folder (no raw/): {p}")
    return p.resolve()


# Paste INSIDE the script's (function(){ ... })(): the bridge returns only the last expression's value.
ACTIVATE = r"""
var __activate = function(P, NAME){
  var cur = app.project ? app.project.path : "";
  if (cur !== P) app.openDocument(P);
  var p = app.project; if (p.path !== P) return "ERROR: could not activate " + P;
  for (var i = 0; i < p.sequences.numSequences; i++) if (p.sequences[i].name === NAME) p.activeSequence = p.sequences[i];
  if (!p.activeSequence || p.activeSequence.name !== NAME) return "ERROR: sequence " + NAME + " not found";
  return null;
};
"""
