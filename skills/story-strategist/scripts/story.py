#!/usr/bin/env python3
"""Validate a story sequence and print it as a storyboard.

  story.py sequence.json
  story.py sequence.json --md storyboard.md
  story.py --stickers                       sticker reference
  story.py sequence.json --json

Sequence format (JSON):
  {
    "date": "2026-11-12",
    "goal": "Get keyword DMs for the starter checklist",
    "frames": [
      {"purpose": "hook", "type": "video", "script": "...", "on_screen": "...", "visual": "...",
       "sticker": {"type": "poll", "prompt": "...", "options": ["...", "..."]}},
      ...
    ]
  }
purpose: hook context value interact proof convert close
type: video photo text
sticker (optional, or "stickers": [...]): see stickers.json

Checks the funnel order (interaction before the ask), one interactive sticker
per frame, sticker option counts, link stickers having a destination,
on-screen text length, and how much of the sequence is selling.
Exit 0 READY, 1 REVIEW, 2 BLOCKED.
"""

import argparse
import json
import os
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, lexicon as L, paths, report as R, text as T

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ref():
    return paths.load_json(os.path.join(HERE, "stickers.json"))


def frame_stickers(f):
    if f.get("stickers"):
        return list(f["stickers"])
    return [f["sticker"]] if f.get("sticker") else []


def validate(seq, wpm=160):
    r = ref()
    plat = paths.load_config("platform")["story"]
    checks = []

    def add(level, cid, msg, frame=None):
        checks.append({"level": level, "id": cid, "frame": frame, "message": msg})

    frames = seq.get("frames") or []
    n = len(frames)
    lo, hi = r["sequence"]["recommended_frames"]
    if n == 0:
        add("FAIL", "empty", "No frames.")
        return checks
    add("PASS" if lo <= n <= hi else "WARN", "count",
        "%d frames%s." % (n, "" if lo <= n <= hi else " (aim for %d-%d; drop-off rises with every tap)" % (lo, hi)))

    first_interact = first_convert = None
    links = 0
    for i, f in enumerate(frames, 1):
        purpose = f.get("purpose", "")
        if purpose not in r["purposes"]:
            add("WARN", "purpose", "Unknown purpose '%s'." % purpose, i)
        st = frame_stickers(f)
        inter = [s for s in st if s.get("type") in r["interactive"]]
        if len(inter) > 1:
            add("WARN", "stickers", "%d interactive stickers on one frame. One per frame gets more taps." % len(inter), i)
        for s in st:
            t = s.get("type")
            info = r["stickers"].get(t)
            if not info:
                add("WARN", "sticker_type", "Unknown sticker '%s'." % t, i)
                continue
            opts = s.get("options") or []
            if "options_max" in info and not info["options_min"] <= len(opts) <= info["options_max"]:
                add("FAIL", "options", "%s needs %d-%d options, has %d." % (t, info["options_min"], info["options_max"], len(opts)), i)
            if info.get("needs_correct") and s.get("correct") is None:
                add("WARN", "quiz", "Quiz has no 'correct' option index.", i)
            if info.get("needs_url") and not (s.get("url") or s.get("destination")):
                add("FAIL", "link", "Link sticker has no url/destination.", i)
            if t == "link":
                links += 1
            if t in ("poll", "quiz", "question", "slider", "add_yours") and first_interact is None:
                first_interact = i
        if purpose == "interact" and first_interact is None:
            first_interact = i
        if purpose == "convert" and first_convert is None:
            first_convert = i
        ost = f.get("on_screen", "")
        if T.word_count(ost) > r["sequence"]["on_screen_max_words"]:
            add("WARN", "text", "On-screen text is %d words. Stories get about 5 seconds of attention." % T.word_count(ost), i)
        secs = T.speech_seconds(f.get("script", ""), wpm) if f.get("script") else 0
        if secs > plat["video_frame_seconds"]["value"]:
            add("WARN", "long", "Script runs ~%.0fs; it will split across frames." % secs, i)
        if L.invisible_chars(f.get("script", "") + ost):
            add("FAIL", "invisible", "Invisible characters.", i)

    if frames[0].get("purpose") not in ("hook", "context"):
        add("WARN", "opening", "Frame 1 is '%s'. Open with a hook or context, not an ask." % frames[0].get("purpose"), 1)
    if first_convert and (first_interact is None or first_convert < first_interact):
        add("WARN", "funnel", "The ask comes before any interaction. Get a tap first (poll, quiz, question), then ask.", first_convert)
    conv = sum(1 for f in frames if f.get("purpose") == "convert")
    if n and conv / n > r["sequence"]["max_convert_share"]:
        add("WARN", "selling", "%d of %d frames are asks. Keep selling under %d%% of the sequence." % (conv, n, round(100 * r["sequence"]["max_convert_share"])))
    if links > 1:
        add("WARN", "links", "%d link stickers. One destination per sequence." % links)
    if first_interact is None:
        add("INFO", "no_interact", "No interactive sticker. Fine for a pure update; otherwise add a poll or question.")
    return checks


def storyboard_md(seq, checks):
    out = ["# Stories: %s" % seq.get("date", ""), "", "**Goal:** %s" % seq.get("goal", "not set"), ""]
    out += ["| # | purpose | type | on screen | sticker | script / visual |", "| --- | --- | --- | --- | --- | --- |"]
    for i, f in enumerate(seq.get("frames", []), 1):
        st = "; ".join("%s: %s%s" % (s.get("type"), s.get("prompt", ""), (" [" + " / ".join(s.get("options", [])) + "]") if s.get("options") else "")
                       for s in frame_stickers(f))
        body = " ".join(x for x in (f.get("script", ""), ("_%s_" % f["visual"]) if f.get("visual") else "") if x)
        out.append("| %d | %s | %s | %s | %s | %s |" % (i, f.get("purpose", ""), f.get("type", ""),
                                                      f.get("on_screen", "").replace("|", "/"), st.replace("|", "/"), body.replace("|", "/")))
    issues = [c for c in checks if c["level"] in ("WARN", "FAIL")]
    if issues:
        out += ["", "## To fix", ""] + ["- %s%s" % (("frame %d: " % c["frame"]) if c["frame"] else "", c["message"]) for c in issues]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--md")
    ap.add_argument("--stickers", action="store_true")
    cli.add_common(ap, keywords=False)
    args = ap.parse_args(argv)
    if args.stickers:
        r = ref()
        if args.json:
            R.emit_json(r)
        else:
            print(R.table([(k, ", ".join(v["best_at"]), v["job"]) for k, v in r["stickers"].items()], ["sticker", "best at", "job"]))
        return 0
    if not args.file:
        ap.error("give a sequence file, or --stickers")
    ctx, prof = cli.build_ctx(args, use_profile_keywords=False)
    wpm = (ctx.get("profile") or {}).get("voice", {}).get("pace_wpm") or 160
    try:
        seq = json.loads(paths.read_text(args.file))
    except ValueError as exc:
        print("BLOCKED: not valid JSON (%s)" % exc)
        return 2
    checks = validate(seq, wpm)
    alltext = "\n".join(f.get("script", "") + "\n" + f.get("on_screen", "") for f in seq.get("frames", []))
    human = engine.score(alltext, "human", ctx) if alltext.strip() else None
    verdict = R.verdict(checks)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(storyboard_md(seq, checks))
    if args.json:
        R.emit_json({"verdict": verdict, "checks": checks, "human": human and human["score"]})
    else:
        print("STORY SEQUENCE  %s  (%d frames)  goal: %s" % (seq.get("date", ""), len(seq.get("frames", [])), seq.get("goal", "not set")))
        print("=" * 78)
        for i, f in enumerate(seq.get("frames", []), 1):
            st = ", ".join(s.get("type", "?") for s in frame_stickers(f)) or "-"
            print("  %2d  %-9s %-6s sticker: %-10s %s" % (i, f.get("purpose", ""), f.get("type", ""), st, (f.get("on_screen") or f.get("script", ""))[:40]))
        print()
        for c in checks:
            print("  %-5s %s%s" % (c["level"], ("frame %d: " % c["frame"]) if c["frame"] else "", c["message"]))
        if human:
            print("\n  human writing %5.1f %s" % (human["score"], human["band"]))
        if args.md:
            print("  Storyboard: " + args.md)
        print("VERDICT: %s" % verdict)
    return {"READY": 0, "REVIEW": 1, "BLOCKED": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
