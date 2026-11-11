#!/usr/bin/env python3
"""The humanizer's two tools.

  rewrite_check.py clean draft.txt [--out clean.txt] [--dashes auto|comma|keep] [--straight-quotes]
      Mechanical, lossless-in-meaning fixes: removes invisible / format
      characters, swaps no-break spaces for spaces, rewrites clause dashes,
      tidies whitespace. Prints the cleaned text; the change log goes to stderr.

  rewrite_check.py report draft.txt [--original before.txt] [--json]
      The quality report: human-writing score with reasons, every flagged span
      with its line number and a plain-language suggestion, and (with
      --original) whether the edit preserved the creator's voice.

These are local heuristics. They do not call any AI detector and cannot
promise how a detector will classify the text. The goal is better writing.
"""

import argparse
import json
import os
import re
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, features as F, lexicon as L, paths, profile as P, report as R, text as T

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPACE_LIKE = {"00A0", "202F"}


def clean(text, dashes="auto", straight_quotes=False):
    log = []
    inv = L.invisible_chars(text)
    if inv:
        drop = {i for i, code, _ in inv if code not in SPACE_LIKE}
        space = {i for i, code, _ in inv if code in SPACE_LIKE}
        counts = {}
        for _, code, name in inv:
            counts[name] = counts.get(name, 0) + 1
        text = "".join(" " if i in space else ch for i, ch in enumerate(text) if i not in drop)
        for name, n in sorted(counts.items()):
            log.append("removed %d x %s" % (n, name))

    if dashes != "keep":
        before = text
        text = re.sub(r"(?<=\d)\s?[–—]\s?(?=\d)", "-", text)  # ranges: 2020–2024 -> 2020-2024
        if dashes == "comma":
            text = re.sub(r"\s*[—―–]\s*", ", ", text)
        else:
            # A dash before a capital or at a clause break becomes a full stop; otherwise a comma.
            text = re.sub(r"\s*[—―–]\s*(?=[A-Z])", ". ", text)
            text = re.sub(r"\s+[—―–]\s+|[—―]", ", ", text)
        n = sum(before.count(d) for d in "—―–")
        if n:
            log.append("rewrote %d dash(es) (%s)" % (n, dashes))

    if straight_quotes:
        before = text
        text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
        if before != text:
            log.append("straightened quotes")

    tidy = re.sub(r"[ \t]+\n", "\n", text)
    tidy = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", tidy)
    tidy = re.sub(r" ,", ",", tidy)
    tidy = re.sub(r",\s*,", ",", tidy)
    tidy = re.sub(r"\.\s*\.(?!\.)", ".", tidy)
    if tidy != text:
        log.append("tidied whitespace / punctuation")
    return tidy, log


def _line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def findings(text, profile):
    sugg = paths.load_json(os.path.join(HERE, "replacements.json"))["suggestions"]
    out = []
    low = text.replace("’", "'").lower()
    for term, _ in L.slop_hits(text):
        for m in re.finditer(r"(?<![\w'])" + re.escape(term) + r"(?![\w'])", low):
            out.append({"line": _line_of(text, m.start()), "kind": "slop", "text": text[m.start():m.end()],
                        "suggest": sugg.get(term, "say the specific thing")})
    for t in L.tells(text):
        idx = text.find(t["match"])
        out.append({"line": _line_of(text, max(idx, 0)), "kind": "template", "text": t["match"], "suggest": t["message"]})
    for term in L.lexicon()["hedges"]:
        for m in re.finditer(r"(?<![\w'])" + re.escape(term) + r"(?![\w'])", low):
            out.append({"line": _line_of(text, m.start()), "kind": "hedge", "text": text[m.start():m.end()],
                        "suggest": "commit or cut"})
    for i, ch in enumerate(text):
        if ch in "—―–" and not (i and text[i - 1].isdigit()):
            out.append({"line": _line_of(text, i), "kind": "dash", "text": ch, "suggest": "full stop or comma"})
    for m in F.TRIAD_RE.finditer(text):
        out.append({"line": _line_of(text, m.start()), "kind": "triad", "text": m.group(0), "suggest": "keep the strongest item"})
    banned = (P.get(profile or {}, "voice.words_i_never_use") or []) + (P.get(profile or {}, "restrictions.never_say") or [])
    for term in banned:
        for m in re.finditer(r"(?<![\w'])" + re.escape(term.lower()) + r"(?![\w'])", low):
            out.append({"line": _line_of(text, m.start()), "kind": "banned", "text": text[m.start():m.end()],
                        "suggest": "creator never says this"})
    for i, code, name in L.invisible_chars(text):
        out.append({"line": _line_of(text, i), "kind": "invisible", "text": "U+" + code, "suggest": "run clean (" + name + ")"})
    sents = T.sentences(text)
    firsts = {}
    for s in sents:
        w = T.lower_words(s)
        if w:
            firsts[w[0]] = firsts.get(w[0], 0) + 1
    for w, n in firsts.items():
        if len(sents) >= 4 and n / len(sents) > 0.3 and n >= 3:
            out.append({"line": 0, "kind": "openers", "text": "%d of %d sentences start with '%s'" % (n, len(sents), w),
                        "suggest": "vary the openings"})
    return sorted(out, key=lambda f: (f["line"], f["kind"]))


def voice_check(original, edited, profile):
    """Did the edit keep the creator's voice? Returns dict of observations."""
    ow = [w for w in T.lower_words(original) if len(w) > 3 and w not in F.STOP]
    ew = set(T.lower_words(edited))
    kept = sum(1 for w in set(ow) if w in ew) / len(set(ow)) if ow else None
    o_len, e_len = T.word_count(original), T.word_count(edited)
    uses = P.get(profile or {}, "voice.words_i_use") or []
    lost = [u for u in uses if u.lower() in original.lower() and u.lower() not in edited.lower()]
    o_slop = sum(n for _, n in L.slop_hits(original))
    e_slop = sum(n for _, n in L.slop_hits(edited))
    notes = []
    if kept is not None and kept < 0.6:
        notes.append("Less than 60% of the original content words survived. Check the meaning did not drift.")
    if o_len and abs(e_len - o_len) / o_len > 0.35:
        notes.append("Length changed by %+d%%." % round(100.0 * (e_len - o_len) / o_len))
    if lost:
        notes.append("Dropped the creator's own phrases: " + ", ".join(lost))
    if e_slop > o_slop:
        notes.append("The edit added slop (%d -> %d)." % (o_slop, e_slop))
    o_ex, e_ex = original.count("!"), edited.count("!")
    if e_ex > o_ex + 1:
        notes.append("More exclamation marks than the original (%d -> %d)." % (o_ex, e_ex))
    return {"content_words_kept": round(kept, 2) if kept is not None else None, "words_before": o_len,
            "words_after": e_len, "own_phrases_lost": lost, "slop_before": o_slop, "slop_after": e_slop, "notes": notes}


DISCLAIMER = ("Heuristic report. It does not call or emulate any specific AI detector, and no score here "
              "guarantees how a detector or a reader will judge the text.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("clean")
    c.add_argument("file")
    c.add_argument("--out")
    c.add_argument("--dashes", choices=["auto", "comma", "keep"], default="auto")
    c.add_argument("--straight-quotes", action="store_true")
    c.add_argument("--json", action="store_true")
    r = sub.add_parser("report")
    r.add_argument("file")
    r.add_argument("--original", help="the draft before editing, to check voice preservation")
    cli.add_common(r, keywords=False)
    args = ap.parse_args(argv)

    if args.cmd == "clean":
        cleaned, log = clean(paths.read_text(args.file), args.dashes, args.straight_quotes)
        if args.json:
            R.emit_json({"text": cleaned, "changes": log})
            return 0
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(cleaned)
        else:
            sys.stdout.write(cleaned)
        sys.stderr.write("CLEAN: " + ("; ".join(log) if log else "no mechanical changes needed") + "\n")
        return 0

    if args.cmd == "report":
        ctx, prof = cli.build_ctx(args, use_profile_keywords=False)
        text = paths.read_text(args.file)
        res = engine.score(text, "human", ctx)
        finds = findings(text, ctx.get("profile"))
        voice = voice_check(paths.read_text(args.original), text, ctx.get("profile")) if args.original else None
        if args.json:
            R.emit_json({"score": res, "findings": finds, "voice": voice, "disclaimer": DISCLAIMER})
            return 0
        print(engine.render(res, show_limits=False))
        print()
        print("FINDINGS (%d)" % len(finds))
        if finds:
            print(R.table([(f["line"] or "-", f["kind"], f["text"][:40], f["suggest"]) for f in finds],
                          ["line", "kind", "text", "suggestion"]))
        if voice:
            print()
            print("VOICE CHECK  kept %s of content words, %d -> %d words, slop %d -> %d" % (
                voice["content_words_kept"], voice["words_before"], voice["words_after"],
                voice["slop_before"], voice["slop_after"]))
            for n in voice["notes"] or ["No voice drift detected."]:
                print("  - " + n)
        print()
        print(DISCLAIMER)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
