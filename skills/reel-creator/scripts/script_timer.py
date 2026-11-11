#!/usr/bin/env python3
"""Estimate how long each line of a reel script takes to say, then check pacing and edit gaps before you film.

  script_timer.py script.txt
  script_timer.py script.txt --target 30
  script_timer.py script.txt --wpm 170 --json

Script format: one beat per line. Optional LABEL: prefix (HOOK:, CTA:, ...).
Annotations in square brackets are not spoken:
  [text: words on screen]   on-screen text (also [os: ...])
  [visual: what we see]     shot / b-roll (also [broll: ...], [shot: ...])
  [cut] [zoom] [jump cut]   edit / transition notes ([edit: ...], [transition: ...])
  [hold: 1.5]               seconds for a silent visual beat
(pause 0.5) inside a line adds a spoken pause. Lines starting with # are ignored.

Flags: hook over ~4 s (aim for 3), a long beat with no visual change, on-screen text that
cannot be read in the time it is up, three abstract beats in a row, no
on-screen text on the hook, no ask at the end, and duration off target.
Timing is an estimate from word counts at your speaking pace; your edit decides.
"""

import argparse
import re
import sys

import _bootstrap  # noqa: F401
from igkit import cli, features as F, lexicon as L, paths, profile as P, report as R, text as T

ANN_RE = re.compile(r"\[([^\]]+)\]")
LABEL_RE = re.compile(r"^\s*([A-Z][A-Z0-9 /-]{1,20}):\s*")
ON_SCREEN = ("text", "os", "on-screen", "onscreen", "caption")
VISUAL = ("visual", "broll", "b-roll", "shot", "show", "scene")
EDIT = ("edit", "transition", "cut", "zoom", "jump cut", "sfx", "music", "whip", "match cut", "speed ramp")

DEFAULTS = {"hook_max": 4.0, "long_beat": 6.0, "silent_beat": 1.0, "target_tolerance": 0.15}


def parse(script):
    beats = []
    for raw in script.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        b = {"label": "", "spoken": "", "on_screen": [], "visual": [], "edit": [], "hold": None, "raw": line}
        m = LABEL_RE.match(line)
        if m:
            b["label"] = m.group(1).strip()
            line = line[m.end():]
        for ann in ANN_RE.findall(line):
            key, _, val = ann.partition(":")
            key, val = key.strip().lower(), val.strip()
            if key in ON_SCREEN:
                b["on_screen"].append(val)
            elif key in VISUAL:
                b["visual"].append(val)
            elif key == "hold":
                try:
                    b["hold"] = float(val.rstrip("s"))
                except ValueError:
                    pass
            elif key in EDIT or any(key.startswith(e) for e in EDIT):
                b["edit"].append(ann.strip())
            else:
                b["visual"].append(ann.strip())
        b["spoken"] = re.sub(r"\s+", " ", ANN_RE.sub(" ", line)).strip()
        beats.append(b)
    return beats


def fmt_tc(s):
    return "%d:%04.1f" % (int(s // 60), s % 60)


def time_beats(beats, wpm, cfg):
    t = 0.0
    for b in beats:
        dur = T.speech_seconds(b["spoken"], wpm) if T.words(T.PAUSE_RE.sub(" ", b["spoken"])) else 0.0
        if b["hold"] is not None:
            dur = max(dur, b["hold"])
        if dur == 0:
            dur = cfg["silent_beat"]
        b["start"], b["seconds"] = round(t, 2), round(dur, 2)
        t += dur
        b["end"] = round(t, 2)
        b["reading_seconds"] = T.reading_seconds(" ".join(b["on_screen"]))
        b["specific"] = F.specificity_hits(b["spoken"]) > 0 or bool(b["visual"])
    return round(t, 2)


def flag(beats, total, target, cfg):
    flags = []

    def add(level, idx, msg):
        flags.append({"level": level, "beat": idx, "message": msg})

    if not beats:
        add("FAIL", 0, "No beats found.")
        return flags
    hook = beats[0]
    if hook["seconds"] > cfg["hook_max"]:
        add("WARN", 1, "Hook takes %.1fs to say; aim for about 3s (flagged above %.0fs)." % (hook["seconds"], cfg["hook_max"]))
    if not hook["on_screen"]:
        add("WARN", 1, "No on-screen text on the hook. Many viewers start muted; add [text: ...].")
    for i, b in enumerate(beats, 1):
        if b["seconds"] > cfg["long_beat"] and not (b["visual"] or b["edit"]):
            add("WARN", i, "%.1fs beat with no visual change. Add a cut, b-roll or zoom, or split the line." % b["seconds"])
        if b["on_screen"] and b["reading_seconds"] > b["seconds"] + 0.25:
            add("WARN", i, "On-screen text needs ~%.1fs to read but is up for %.1fs. Shorten it." % (b["reading_seconds"], b["seconds"]))
    run = 0
    for i, b in enumerate(beats, 1):
        run = 0 if b["specific"] else run + 1
        if run == 3:
            add("WARN", i, "Three beats in a row with nothing concrete (no number, name, object or visual). Viewers drift here.")
    last = beats[-1]
    if not (L.asks(last["spoken"]) or last["label"].upper().startswith("CTA") or last["spoken"].endswith("?")):
        add("INFO", len(beats), "Last beat has no ask or question. Fine if the ending loops; otherwise add the CTA.")
    first_w = {w for w in T.lower_words(hook["spoken"]) if len(w) > 3 and w not in F.STOP}
    last_w = {w for w in T.lower_words(last["spoken"]) if len(w) > 3 and w not in F.STOP}
    if first_w and not (first_w & last_w):
        add("INFO", len(beats), "The ending does not echo the hook. A line that calls back to the start can make the loop seamless.")
    if target:
        diff = (total - target) / target
        if abs(diff) > cfg["target_tolerance"]:
            add("WARN", 0, "Runs %.1fs against a %.0fs target (%+d%%)." % (total, target, round(100 * diff)))
        else:
            add("PASS", 0, "%.1fs is within %d%% of the %.0fs target." % (total, round(100 * cfg["target_tolerance"]), target))
    return flags


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="script file or -")
    ap.add_argument("--target", type=float, help="intended reel length (s); warns if the estimate is more than 15%% off")
    ap.add_argument("--wpm", type=float, help="speaking pace (default: profile voice.pace_wpm or 160)")
    ap.add_argument("--hook-max", type=float, default=DEFAULTS["hook_max"])
    cli.add_common(ap, keywords=False)
    args = ap.parse_args(argv)
    ctx, prof = cli.build_ctx(args, use_profile_keywords=False)
    wpm = args.wpm or P.get(ctx.get("profile") or {}, "voice.pace_wpm") or 160
    cfg = dict(DEFAULTS, hook_max=args.hook_max)

    beats = parse(paths.read_text(args.file))
    total = time_beats(beats, wpm, cfg)
    flags = flag(beats, total, args.target, cfg)
    words = sum(T.spoken_word_count(T.PAUSE_RE.sub(" ", b["spoken"])) for b in beats)

    if args.json:
        R.emit_json({"wpm": wpm, "total_seconds": total, "spoken_words": words, "target": args.target,
                     "beats": [{k: v for k, v in b.items() if k != "raw"} for b in beats], "flags": flags})
        return 1 if any(f["level"] in ("FAIL", "WARN") for f in flags) else 0

    head = "BEAT SHEET  %d beats  %d spoken words  ~%.1fs at %g wpm" % (len(beats), words, total, wpm)
    if args.target:
        head += "  target %.0fs" % args.target
    print(head)
    print("=" * 78)
    rows = []
    for i, b in enumerate(beats, 1):
        rows.append((i, "%s-%s" % (fmt_tc(b["start"]), fmt_tc(b["end"])), b["label"] or "",
                     (b["spoken"][:38] + "...") if len(b["spoken"]) > 41 else b["spoken"],
                     "; ".join(b["on_screen"])[:22], "; ".join(b["visual"] + b["edit"])[:24]))
    print(R.table(rows, ["#", "time", "label", "spoken", "on-screen", "visual / edit"]))
    print()
    for f in flags:
        where = ("beat %d: " % f["beat"]) if f["beat"] else ""
        print("  %-5s %s%s" % (f["level"], where, f["message"]))
    if not flags:
        print("  PASS  no timing problems found")
    print("\nEstimates only: real timing depends on delivery and the edit.")
    return 1 if any(f["level"] in ("FAIL", "WARN") for f in flags) else 0


if __name__ == "__main__":
    sys.exit(main())
