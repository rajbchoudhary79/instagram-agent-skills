#!/usr/bin/env python3
"""Find the clip-worthy moments in a long transcript (video, podcast, livestream, article).

  segment.py episode.srt                    SRT or WebVTT: real timestamps
  segment.py article.txt                    plain text: positions estimated at 150 wpm (marked ~)
  segment.py episode.vtt --window 45 --top 8
  segment.py episode.srt --json > moments.json

Each window (default ~45 s) is scored on: the best hook-like sentence in it
(hook rubric), concrete detail, stakes, story shape and reusable value. The
output is a ranked shortlist with timestamps, the candidate hook sentence and
a suggested format. The agent then reads the shortlisted passages in full;
nothing here decides what the creator meant.
"""

import argparse
import re
import sys

import _bootstrap  # noqa: F401
from igkit import engine, features as F, lexicon as L, paths, report as R, text as T

TS_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
WPM_EST = 150.0


def _ts(s):
    m = TS_RE.search(s)
    if not m:
        return None
    h = int(m.group(1) or 0)
    return h * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4).ljust(3, "0")) / 1000.0


def parse(raw, name=""):
    """Return (cues, timed). cue = {'start', 'end', 'text'}."""
    if "-->" in raw:
        cues = []
        for block in re.split(r"\n\s*\n", raw.replace("\r", "")):
            lines = [ln for ln in block.strip().splitlines() if ln.strip()]
            idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
            if idx is None:
                continue
            a, _, b = lines[idx].partition("-->")
            text = " ".join(re.sub(r"<[^>]+>", "", ln) for ln in lines[idx + 1:]).strip()
            if text and _ts(a) is not None:
                cues.append({"start": _ts(a), "end": _ts(b) or _ts(a), "text": text})
        return cues, True
    cues, t = [], 0.0
    for s in T.sentences(raw):
        d = T.word_count(s) / (WPM_EST / 60.0)
        cues.append({"start": t, "end": t + d, "text": s})
        t += d
    return cues, False


def windows(cues, size):
    out, cur = [], []
    for c in cues:
        cur.append(c)
        span = cur[-1]["end"] - cur[0]["start"]
        if span >= size and re.search(r"[.!?…][\"'”’)]*$", c["text"]):
            out.append(cur)
            cur = []
        elif span >= size * 1.6:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def score_window(win, formulas):
    text = " ".join(c["text"] for c in win)
    sents = [s for s in T.sentences(text) if 4 <= T.word_count(s) <= 22]
    best, best_s = None, 0.0
    for s in sents:
        sc = engine.score(s, "hook", {"formulas": formulas})["score"]
        if sc > best_s:
            best, best_s = s, sc
    spec = F.compute("specificity_hits", text)
    arc = F.compute("story_arc", text)
    value = F.compute("value_markers", text)
    stakes = F.compute("stakes", text)
    parts = {
        "hook": best_s,
        "detail": min(100.0, spec * 20.0),
        "story": 100.0 * arc / 3,
        "value": min(100.0, value * 34),
        "stakes": min(100.0, stakes * 20),
    }
    weights = {"hook": 0.35, "detail": 0.2, "story": 0.15, "value": 0.15, "stakes": 0.15}
    total = sum(parts[k] * w for k, w in weights.items())
    if parts["value"] >= 67 and parts["story"] < 67:
        fmt = "carousel"
    elif parts["story"] >= 67 or parts["stakes"] >= 60:
        fmt = "reel"
    else:
        fmt = "reel or carousel"
    return {"start": win[0]["start"], "end": win[-1]["end"], "words": T.word_count(text), "score": round(total, 1),
            "parts": {k: round(v) for k, v in parts.items()}, "hook": best, "format": fmt, "text": text}


def fmt_ts(s, timed):
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    out = ("%d:%02d:%02d" % (h, m, sec)) if h else ("%d:%02d" % (m, sec))
    return out if timed else "~" + out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--window", type=float, default=45.0, help="target window length in seconds")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    raw = paths.read_text(args.file)
    cues, timed = parse(raw, args.file)
    if not cues:
        print("No text found.")
        return 1
    formulas = paths.load_config("hook_formulas")["formulas"]
    wins = [score_window(w, formulas) for w in windows(cues, args.window)]
    ranked = sorted(wins, key=lambda w: w["score"], reverse=True)[: args.top]
    total = cues[-1]["end"]
    if args.json:
        R.emit_json({"timed": timed, "duration_seconds": round(total, 1), "windows": len(wins), "moments": ranked})
        return 0
    print("MOMENTS  %s  %s%s, %d windows, top %d" % (args.file, "" if timed else "~", fmt_ts(total, True), len(wins), len(ranked)))
    if not timed:
        print("(plain text: positions estimated at %d wpm, marked ~)" % WPM_EST)
    print("=" * 78)
    for i, w in enumerate(ranked, 1):
        print("%d. %s-%s  score %.0f  -> %s" % (i, fmt_ts(w["start"], timed), fmt_ts(w["end"], timed), w["score"], w["format"]))
        print("   hook candidate: %s" % (w["hook"] or "(none: write one from the passage)"))
        print("   " + "  ".join("%s %d" % (k, v) for k, v in w["parts"].items()))
        print("   \"%s\"" % (w["text"][:160] + ("..." if len(w["text"]) > 160 else "")))
        print()
    print("Shortlist only. Read each passage in full before writing; keep the speaker's meaning.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
