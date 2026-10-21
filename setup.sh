#!/usr/bin/env bash
# setup.sh — ONE-COMMAND auto-setup. Detects your OS (macOS, Windows or Linux), installs
# everything the pipeline needs, bootstraps the render engine, verifies with
# check-setup.sh, then auto-detects your editing app (Premiere / Resolve / CapCut)
# and wires its lane. Safe to re-run any time: it skips what's already done and
# picks up where it left off (e.g. after a restart that refreshed PATH).
#
#   ./setup.sh
#   ./setup.sh --lane premiere|resolve|capcut|chat-only
#       records the user's editing-app pick (asked only when several apps are
#       installed) and, for premiere/resolve, runs that lane's installer.
#
# macOS:   installs via Homebrew (if Homebrew itself is missing, you run its one-liner
#          once (it needs your password), then re-run this; it finds the new Homebrew in
#          /opt/homebrew or /usr/local on its own and adds it to your shell profile).
# Windows: run from Git Bash (the shell Claude Code uses on Windows); installs via
#          winget. Newly installed tools sometimes need a new terminal before they're
#          on PATH; this script pulls in their well-known install dirs so most setups
#          finish in ONE run; if anything is still pending it says exactly what to do.
# Linux:   tools are not auto-installed (./check-setup.sh prints the apt command
#          for each missing one), but everything else runs: verify, render-engine
#          bootstrap, Resolve lane detection (/opt/resolve), the done marker.
#
# Exit codes (Claude reads these; each prints exactly what to do):
#   0  done (output may carry an ACTION FOR CLAUDE line: the which-app question)
#   1  something needs fixing before continuing; the output says what (Homebrew
#      missing on macOS, brew/apt installs that did not land, a lane installer that failed)
#   2  restart needed: freshly installed tools (or Homebrew's PATH) aren't visible to
#      this session yet. Restart Claude Code, then re-run ./setup.sh; it finishes the rest.
#   3  an editing-app MCP lane was just wired into .mcp.json. Restart Claude Code
#      so it loads the new MCP (answer YES when it asks to enable this project's
#      .mcp.json servers), then verify the lane.
#
# State: .setup-complete (written once every core tool verifies) carries ONE line,
#   lane=<premiere|resolve|capcut|chat-only|pending>
# so a later session knows which finish surface this machine uses. "pending" means the
# which-app question is still open; the SessionStart hook keeps reminding Claude until
# ./setup.sh --lane <pick> records the answer.
#
# This handles tools + the editing-app lane. Personalization (brand-kit.md) is
# OPTIONAL and separate: the editor works out of the box with the neutral bundled
# look; fill the brand kit in whenever (or never).
set -uo pipefail

# Resolve the PROJECT root. In the shipped package this script sits at the root;
# in the source repo it lives under packaging/overlay/. The marker file decides.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$HERE/check-setup.sh" ]; then
  ROOT="$HERE"
elif [ -f "$HERE/../../check-setup.sh" ]; then
  ROOT="$(cd "$HERE/../.." && pwd)"
else
  printf 'ERROR: cannot locate the project root (check-setup.sh not found)\n' >&2
  exit 1
fi
cd "$ROOT"

HF_PIN="0.8.16"   # keep in sync with the pin in CLAUDE.md / SETUP.md

say()  { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

# ─── arguments ───────────────────────────────────────────────────────────────
LANE_PICK=""
while [ $# -gt 0 ]; do
  case "$1" in
    --lane)
      shift
      case "${1:-}" in
        premiere|resolve|capcut|chat-only) LANE_PICK="$1" ;;
        *) say "usage: ./setup.sh [--lane premiere|resolve|capcut|chat-only]"; exit 1 ;;
      esac ;;
    --lane=*)
      case "${1#--lane=}" in
        premiere|resolve|capcut|chat-only) LANE_PICK="${1#--lane=}" ;;
        *) say "usage: ./setup.sh [--lane premiere|resolve|capcut|chat-only]"; exit 1 ;;
      esac ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) say "unknown option: $1"; say "usage: ./setup.sh [--lane premiere|resolve|capcut|chat-only]"; exit 1 ;;
  esac
  shift
done

MARKER="$ROOT/.setup-complete"
record_lane() { printf 'lane=%s\n' "$1" > "$MARKER"; }
recorded_lane() { sed -n 's/^lane=//p' "$MARKER" 2>/dev/null | head -n 1; }

UNAME="$(uname -s 2>/dev/null || echo unknown)"
case "$UNAME" in
  Darwin)               OS=mac ;;
  MINGW*|MSYS*|CYGWIN*) OS=windows ;;
  Linux)                OS=linux ;;
  *)                    OS=other ;;
esac

# Python probe: Windows installs Python as `python` (its `python3` is a fake
# Microsoft Store stub), so probe by RUNNING it, never by `command -v`.
pybin() {
  if python3 -c '' >/dev/null 2>&1; then echo python3
  elif python -c '' >/dev/null 2>&1; then echo python
  else echo ""; fi
}

# ─────────────────────────────────────────────────────────────────────────────
if [ "$OS" = other ]; then
  say "Unrecognized shell/OS ($UNAME)."
  say "On Windows, run this from Git Bash (installed with Git for Windows: winget install Git.Git)."
  exit 1
fi

case "$OS" in mac) OSLBL="macOS" ;; windows) OSLBL="Windows · Git Bash" ;; *) OSLBL="Linux" ;; esac
say "== video-editor auto-setup ($OSLBL) =="
say ""
if [ "$OS" = linux ]; then
  say "Linux: tools are not auto-installed here. If the verify below finds anything"
  say "missing, run the exact apt commands it prints, then re-run ./setup.sh."
  say ""
fi

PENDING=0        # 1 when something needs a restart/new terminal before it's usable
PENDING_WHY=""   # one line saying what

# ─── macOS: Homebrew installs ────────────────────────────────────────────────
if [ "$OS" = mac ]; then
  # Homebrew installs to /opt/homebrew (Apple Silicon) or /usr/local (Intel), and neither
  # is on the default PATH: right after its installer finishes, `brew` is invisible to the
  # shell that ran it. Find it there, put it on THIS process's PATH so the run can finish,
  # and add Homebrew's own shellenv line to the login profile so every later shell sees it.
  BREW_OFF_PATH=""
  if ! have brew; then
    for b in /opt/homebrew/bin /usr/local/bin; do
      if [ -x "$b/brew" ]; then BREW_OFF_PATH="$b"; PATH="$b:$PATH"; export PATH; break; fi
    done
  fi
  if ! have brew; then
    say "Homebrew is missing: it's the one step that needs YOUR password, so run this"
    say "in your terminal, then re-run ./setup.sh (it finds the new Homebrew on its own"
    say "and adds it to your shell PATH; nothing else to do):"
    say ''
    say '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
  fi
  if [ -n "$BREW_OFF_PATH" ]; then
    case "$(basename "${SHELL:-/bin/zsh}")" in
      bash) PROFILE="$HOME/.bash_profile" ;;
      zsh)  PROFILE="$HOME/.zprofile" ;;
      *)    PROFILE="$HOME/.profile" ;;
    esac
    say "  ▸ Homebrew is installed at $BREW_OFF_PATH but not on this shell's PATH; adding it to $PROFILE…"
    if ! grep -qsF "$BREW_OFF_PATH/brew shellenv" "$PROFILE"; then
      printf '\n# Homebrew on PATH (added by video-editor setup.sh)\neval "$(%s/brew shellenv)"\n' "$BREW_OFF_PATH" >> "$PROFILE"
    fi
    eval "$("$BREW_OFF_PATH/brew" shellenv)"
    PENDING=1; PENDING_WHY="Homebrew's PATH was added to $PROFILE, which only new sessions read."
  fi
  for pkg in ffmpeg uv node python pillow; do
    case "$pkg" in
      ffmpeg) probe=ffmpeg ;;
      uv)     probe=uv ;;
      node)   probe=node ;;
      python) probe="" ;;   # probed via pybin below
      pillow) probe="" ;;   # probed via import below
    esac
    if [ "$pkg" = python ]; then
      [ -n "$(pybin)" ] && { say "  ✓ python present"; continue; }
    elif [ "$pkg" = pillow ]; then
      P="$(pybin)"; [ -n "$P" ] && "$P" -c "import PIL" >/dev/null 2>&1 && { say "  ✓ Pillow present"; continue; }
    elif have "$probe"; then
      say "  ✓ $pkg present"; continue
    fi
    say "  ▸ installing $pkg (brew)…"
    brew install "$pkg" || say "  ⚠ brew install $pkg failed; re-run ./setup.sh after fixing the error above"
  done
  # node too old? HyperFrames wants ≥22.
  if have node; then
    NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
    if [ "${NODE_MAJOR:-0}" -lt 22 ]; then
      say "  ▸ node v$(node -v | tr -d v) is too old; upgrading (brew)…"
      brew upgrade node || true
    fi
  fi
fi

# ─── Windows: winget installs + same-session PATH pickup ─────────────────────
if [ "$OS" = windows ]; then
  if ! have winget && ! have winget.exe; then
    say "winget is missing. Install 'App Installer' from the Microsoft Store, then re-run ./setup.sh."
    exit 1
  fi
  wg() {  # wg <winget-id>: quiet, license-accepted, exact-id install
    winget install --exact --id "$1" --accept-source-agreements --accept-package-agreements \
      --disable-interactivity >/dev/null 2>&1
    rc=$?
    # 0 = installed; winget uses distinct nonzero codes for "already installed"; treat
    # any rc as fine here and let the probe after PATH refresh be the real check.
    return 0
  }
  # Pull freshly installed tools into THIS session's PATH (winget updates the user PATH,
  # but only new terminals see that). Best-effort: well-known install dirs + winget's
  # portable-package folders (Links/ is where portable packages like uv get their shims).
  # Makes one-run setup possible.
  refresh_path() {
    local d
    for d in "/c/Program Files/nodejs" \
             "$(cygpath -u "${LOCALAPPDATA:-}" 2>/dev/null)/Programs/Python/Python312" \
             "$(cygpath -u "${LOCALAPPDATA:-}" 2>/dev/null)/Programs/Python/Python312/Scripts" \
             "$(cygpath -u "${LOCALAPPDATA:-}" 2>/dev/null)/Microsoft/WinGet/Links" \
             "$(cygpath -u "${USERPROFILE:-}" 2>/dev/null)/.local/bin"; do
      [ -d "$d" ] && PATH="$d:$PATH"
    done
    # Gyan.FFmpeg is a winget "portable" package; its bin lands under WinGet/Packages
    for d in "$(cygpath -u "${LOCALAPPDATA:-}" 2>/dev/null)/Microsoft/WinGet/Packages"/Gyan.FFmpeg*/ffmpeg-*/bin; do
      [ -d "$d" ] && PATH="$d:$PATH"
    done
    export PATH
  }

  if have ffmpeg; then say "  ✓ ffmpeg present"; else say "  ▸ installing ffmpeg (winget)…";  wg Gyan.FFmpeg; fi
  if have node;   then say "  ✓ node present";   else say "  ▸ installing node (winget)…";    wg OpenJS.NodeJS.LTS; fi
  if have uv;     then say "  ✓ uv present";     else say "  ▸ installing uv (winget)…";      wg astral-sh.uv; fi
  if [ -n "$(pybin)" ]; then say "  ✓ python present"; else say "  ▸ installing python (winget)…"; wg Python.Python.3.12; fi

  refresh_path

  P="$(pybin)"
  if [ -n "$P" ]; then
    if "$P" -c "import PIL" >/dev/null 2>&1; then
      say "  ✓ Pillow present"
    else
      say "  ▸ installing Pillow (pip)…"
      "$P" -m pip install --quiet pillow || say "  ⚠ pip install pillow failed; re-run ./setup.sh"
    fi
  else
    say "  ⚠ python not visible yet in this session"
    PENDING=1; PENDING_WHY="Just-installed tools are not on this session's PATH yet."
  fi
  for t in ffmpeg node uv; do
    have "$t" || { say "  ⚠ $t not visible yet in this session"; PENDING=1; PENDING_WHY="Just-installed tools are not on this session's PATH yet."; }
  done
fi

# ─── Render-engine bootstrap (all OSes) ──────────────────────────────────────
# `browser ensure` finds or downloads the headless Chrome the renderer uses and exits
# non-zero if it cannot (`doctor` only REPORTS, always exits 0, and downloads nothing,
# so it could never gate the marker). One time; the download is ~90 MB.
say ""
if have npx; then
  if [ -f ".setup-hyperframes-ok" ]; then
    say "  ✓ render engine already bootstrapped (npx hyperframes@$HF_PIN)"
  else
    say "  ▸ bootstrapping the render engine (npx hyperframes@$HF_PIN browser ensure; one time,"
    say "    downloads its headless browser; npm/telemetry notices below are its own and need no action)…"
    if npx -y "hyperframes@$HF_PIN" browser ensure; then
      touch ".setup-hyperframes-ok"
      say "  ✓ render engine ready (pinned to hyperframes@$HF_PIN on purpose; never run 'hyperframes upgrade')"
    else
      say "  ⚠ the render engine could not fetch its headless browser; read its output above"
      say "    (usually network), then re-run ./setup.sh"
    fi
  fi
else
  if [ "$OS" = windows ]; then
    say "  ⚠ npx not available yet; the render-engine bootstrap runs on the next ./setup.sh"
    PENDING=1; PENDING_WHY="Just-installed tools are not on this session's PATH yet."
  else
    # macOS/Linux: node is genuinely missing (nothing installed it this run, or the brew
    # install failed). Fall through so check-setup.sh prints the real install command.
    say "  ⚠ node/npx missing: the check below prints the install command; the render-engine"
    say "    bootstrap runs on the next ./setup.sh"
  fi
fi

# ─── Restart gate ────────────────────────────────────────────────────────────
say ""
if [ "$PENDING" -eq 1 ]; then
  say "== Almost done: this session needs a fresh environment =="
  say "$PENDING_WHY"
  say "One step for you: RESTART Claude Code (quit it fully, then reopen this folder)"
  say "and say \"continue setup\"; it re-runs ./setup.sh, which skips everything"
  say "already done and finishes the rest."
  exit 2
fi

say "== Verifying with check-setup.sh =="
./check-setup.sh || { say ""; say "Fix the items above, then re-run ./setup.sh"; exit 1; }

# Core tools verified: record it so the fresh-install reminder stops firing. The lane line
# is filled in by the block below (a re-run keeps whatever was recorded before).
# (The editing-app lane below and the brand kit are optional layers on top.)
[ -f "$MARKER" ] || record_lane pending
REC_LANE="$(recorded_lane)"

# ─── Editing-app lane (auto-detected, optional) ──────────────────────────────
# If an editing app is installed, settle the lane now so rough cuts can land on a
# real timeline: exactly one app → wire it without asking; several → Claude asks
# the user which they edit in (a script can't) and records the answer with
# ./setup.sh --lane <pick>; none → chat-only finish, done.
say ""
say "== Editing apps =="
DET_PREMIERE=0; DET_RESOLVE=0; DET_CAPCUT=0
if [ "$OS" = mac ]; then
  compgen -G "/Applications/Adobe Premiere Pro*" >/dev/null 2>&1 && DET_PREMIERE=1
  [ -d "/Applications/DaVinci Resolve/DaVinci Resolve.app" ] && DET_RESOLVE=1
  [ -d "/Applications/CapCut.app" ] && DET_CAPCUT=1
elif [ "$OS" = windows ]; then
  compgen -G "/c/Program Files/Adobe/Adobe Premiere Pro*" >/dev/null 2>&1 && DET_PREMIERE=1
  [ -e "/c/Program Files/Blackmagic Design/DaVinci Resolve/Resolve.exe" ] && DET_RESOLVE=1
  # (CapCut lane is macOS-only; its bridge drives the macOS accessibility tree.)
else
  # Linux: Resolve is the only app lane here (native install at /opt/resolve)
  [ -d /opt/resolve ] && DET_RESOLVE=1
fi
# A lane this package does not SHIP (built with package-for-client.sh --lane <app>) is
# never offered, whatever is installed: its installer and skill are not here.
if [ "$DET_PREMIERE" -eq 1 ] && [ ! -d "$ROOT/lanes/premiere" ]; then
  say "  · Premiere Pro detected, but this package does not include the Premiere lane"; DET_PREMIERE=0
fi
if [ "$DET_RESOLVE" -eq 1 ] && [ ! -d "$ROOT/lanes/resolve" ]; then
  say "  · DaVinci Resolve detected, but this package does not include the Resolve lane"; DET_RESOLVE=0
fi
if [ "$DET_CAPCUT" -eq 1 ] && [ ! -d "$ROOT/lanes/capcut" ]; then
  say "  · CapCut detected, but this package does not include the CapCut lane"; DET_CAPCUT=0
fi
# The which-app question counts EVERY installed lane app, CapCut included: a CapCut editor
# with Premiere also installed must be asked, never handed a Premiere lane they never use.
N_APPS=$((DET_PREMIERE + DET_RESOLVE + DET_CAPCUT))
APPS=""
[ "$DET_PREMIERE" -eq 1 ] && APPS="$APPS premiere"
[ "$DET_RESOLVE"  -eq 1 ] && APPS="$APPS resolve"
[ "$DET_CAPCUT"   -eq 1 ] && APPS="$APPS capcut"
APPS="${APPS# }"

# Already wired? (engine built + entry present in .mcp.json)
WIRED_PREMIERE=0; WIRED_RESOLVE=0
[ -f "$ROOT/vendor/premiere-mcp/dist/index.js" ] && grep -qs '"premiere-pro"' "$ROOT/.mcp.json" && WIRED_PREMIERE=1
{ [ -e "$ROOT/vendor/davinci-resolve-mcp/venv/bin/python" ] || [ -e "$ROOT/vendor/davinci-resolve-mcp/venv/Scripts/python.exe" ]; } \
  && grep -qs '"davinci-resolve"' "$ROOT/.mcp.json" && WIRED_RESOLVE=1

# Find the lane installers (package root, or packaging/overlay/ in the source repo)
lane_script() { if [ -f "$ROOT/$1" ]; then echo "$ROOT/$1"; else echo "$HERE/$1"; fi; }
wire() {  # wire premiere|resolve → sets WIRED_NOW or WIRE_FAILED
  case "$1" in
    premiere) label="Premiere Pro";    script=setup-premiere.sh ;;
    *)        label="DaVinci Resolve"; script=setup-resolve.sh ;;
  esac
  say "  ▸ wiring the $label lane (./$script)…"
  if bash "$(lane_script "$script")"; then WIRED_NOW="$1"
  else say "  ⚠ $script failed; read its output above"; WIRE_FAILED="$1"; fi
}

WIRED_NOW=""; WIRE_FAILED=""; ASK_APP=0; LANE=""
[ "$DET_CAPCUT" -eq 1 ] && say "  ✓ CapCut detected: nothing to install for it (its lane works out of the box)"
[ "$DET_PREMIERE" -eq 1 ] && [ "$WIRED_PREMIERE" -eq 1 ] && say "  ✓ Premiere Pro detected, lane already wired"
[ "$DET_RESOLVE"  -eq 1 ] && [ "$WIRED_RESOLVE"  -eq 1 ] && say "  ✓ DaVinci Resolve detected, lane already wired"

if [ -n "$LANE_PICK" ]; then
  # The user's answer to the which-app question (or an explicit switch). Final.
  case "$LANE_PICK" in
    premiere|resolve)
      if [ ! -d "$ROOT/lanes/$LANE_PICK" ]; then
        say "  ✗ this package does not include the $LANE_PICK lane"; exit 1
      fi
      if { [ "$LANE_PICK" = premiere ] && [ "$WIRED_PREMIERE" -eq 1 ]; } || { [ "$LANE_PICK" = resolve ] && [ "$WIRED_RESOLVE" -eq 1 ]; }; then
        say "  ✓ $LANE_PICK lane already wired; recorded as this machine's lane"
      else
        wire "$LANE_PICK"
      fi
      LANE="$LANE_PICK" ;;
    capcut)
      [ "$DET_CAPCUT" -eq 1 ] || say "  · CapCut is not installed in /Applications (recording the pick anyway; install it before the first edit)"
      say "  ✓ CapCut recorded as this machine's lane (nothing to install)"
      LANE=capcut ;;
    chat-only)
      say "  ✓ chat-only finish recorded as this machine's lane (no editing app will be driven)"
      LANE=chat-only ;;
  esac
elif [ "$WIRED_PREMIERE" -eq 1 ] || [ "$WIRED_RESOLVE" -eq 1 ]; then
  # A lane is wired: that is the lane. (Both wired: keep the recorded one, else Premiere.)
  if [ "$WIRED_PREMIERE" -eq 1 ] && [ "$WIRED_RESOLVE" -eq 1 ]; then
    case "$REC_LANE" in premiere|resolve) LANE="$REC_LANE" ;; *) LANE=premiere ;; esac
  elif [ "$WIRED_PREMIERE" -eq 1 ]; then LANE=premiere; else LANE=resolve; fi
  for a in $APPS; do
    case "$a" in
      premiere) [ "$WIRED_PREMIERE" -eq 0 ] && say "  · Premiere Pro is also installed but not wired. That's fine; ./setup.sh --lane premiere switches to it (only if the user asks)." ;;
      resolve)  [ "$WIRED_RESOLVE"  -eq 0 ] && say "  · DaVinci Resolve is also installed but not wired. That's fine; ./setup.sh --lane resolve switches to it (only if the user asks)." ;;
    esac
  done
elif [ "$REC_LANE" = capcut ] || [ "$REC_LANE" = chat-only ]; then
  # A pick that wires nothing, recorded on an earlier run: still the answer.
  say "  ✓ lane recorded earlier: $REC_LANE (./setup.sh --lane <app> switches, only if the user asks)"
  LANE="$REC_LANE"
elif [ "$N_APPS" -eq 0 ]; then
  say "  · no editing app detected: the chat-only pipeline is the finish (nothing to set up)"
  LANE=chat-only
elif [ "$N_APPS" -eq 1 ]; then
  case "$APPS" in
    capcut) LANE=capcut ;;
    *) say "  · $APPS is the only editing app installed, wiring it without asking"; wire "$APPS"; LANE="$APPS" ;;
  esac
else
  ASK_APP=1; LANE=pending
  say "  ? MULTIPLE editing apps detected: $APPS"
  say "    ACTION FOR CLAUDE: ask the user in ONE line which of these they edit in, then run"
  say "    ./setup.sh --lane <their pick>  (premiere | resolve | capcut; or chat-only if they"
  say "    would rather finish in chat). premiere/resolve install that app's MCP lane and end"
  say "    with a restart-Claude-Code step; capcut needs no install."
fi
[ -n "$WIRE_FAILED" ] && LANE=pending
record_lane "$LANE"

# ─── Done ────────────────────────────────────────────────────────────────────
say ""
if [ -n "$WIRE_FAILED" ]; then
  say "== Tools done, but the $WIRE_FAILED lane FAILED to wire =="
  say "ACTION FOR CLAUDE: read the installer error above, fix it, then re-run"
  say "./setup.sh --lane $WIRE_FAILED (tools stay installed; the re-run skips them and retries the lane)."
  exit 1
fi
if [ -n "$WIRED_NOW" ]; then
  say "== Tools done + $WIRED_NOW lane wired (lane=$WIRED_NOW recorded in .setup-complete) =="
  say "One step for you: RESTART Claude Code (quit it fully, then reopen this folder)"
  say "so it loads the new MCP. When Claude Code asks whether to enable the MCP servers"
  say "in this project's .mcp.json, answer YES (a no is remembered; undo it with"
  say "'claude mcp reset-project-choices'). Then say \"continue setup\"; Claude verifies"
  say "the $WIRED_NOW lane with you."
  say ""
  say "Optional, whenever you like: personalize the look/voice via brand-kit.md"
  say "(tell Claude \"apply my brand kit\"). The editor already works without it."
  exit 3
fi

if [ "$ASK_APP" -eq 1 ]; then
  say "== Tools done; one question left (the app pick above, Claude asks it) =="
else
  say "== Setup done (lane=$LANE) =="
  say "Drop a raw clip and tell Claude to edit it. First edit also downloads the"
  say "WhisperX speech model (~3-5 GB, one time)."
fi
say "Optional, whenever you like: personalize the look/voice via brand-kit.md"
say "(tell Claude \"apply my brand kit\"). The editor already works without it."
