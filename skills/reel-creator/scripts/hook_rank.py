#!/usr/bin/env python3
"""Rank reel hooks and explain each score.

  hook_rank.py hooks.txt                 one hook per line (# lines ignored)
  hook_rank.py hooks.txt --detail        full reasoning for every hook
  hook_rank.py --formulas                list the formula library
  hook_rank.py --formulas --family proof
  hook_rank.py --formula wrong_default   one formula in full

Scoring uses config/rubrics/hook.json (editable). Each hook is also timed at
the creator's speaking pace: a hook should be said in about 3 seconds.
Scores are heuristics about the words, not predictions of reach.
"""

import argparse
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, features as F, paths, profile as P, report as R, text as T

HOOK_MAX_SECONDS = 4.0  # aim for ~3s; flag above 4s to allow for estimate error


def score_hooks(hooks, ctx, wpm):
    lib = paths.load_config("hook_formulas")["formulas"]
    ctx = dict(ctx, formulas=lib)
    out = []
    for h in hooks:
        res = engine.score(h, "hook", ctx)
        secs = T.speech_seconds(h, wpm)
        out.append({
            "hook": h, "score": res["score"], "band": res["band"], "weakest": res["weakest"],
            "formulas": F.match_formulas(h, lib), "seconds": secs, "too_long_to_say": secs > HOOK_MAX_SECONDS,
            "dealbreakers": [d["message"] for d in res["dealbreakers"]], "detail": res,
        })
    return sorted(out, key=lambda r: r["score"], reverse=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="hooks file, one per line, or -")
    ap.add_argument("--detail", action="store_true")
    ap.add_argument("--formulas", action="store_true", help="list the formula library")
    ap.add_argument("--family", help="filter --formulas by family")
    ap.add_argument("--formula", help="show one formula by id")
    ap.add_argument("--wpm", type=float, help="speaking pace (default: profile voice.pace_wpm or 160)")
    cli.add_common(ap)
    args = ap.parse_args(argv)
    lib = paths.load_config("hook_formulas")

    if args.formula:
        f = next((x for x in lib["formulas"] if x["id"] == args.formula), None)
        if not f:
            print("no formula '%s'" % args.formula)
            return 1
        for k in ("id", "family", "name", "template", "example", "on_screen", "use_for", "avoid_when", "match"):
            print("%-11s %s" % (k, f[k]))
        return 0
    if args.formulas:
        rows = [(f["id"], f["family"], f["template"]) for f in lib["formulas"]
                if not args.family or f["family"] == args.family]
        if args.json:
            R.emit_json([f for f in lib["formulas"] if not args.family or f["family"] == args.family])
        else:
            print(R.table(rows, ["id", "family", "template"]))
        return 0
    if not args.file:
        ap.error("give a hooks file, or --formulas")

    ctx, prof = cli.build_ctx(args, use_profile_keywords=False)
    wpm = args.wpm or P.get(ctx.get("profile") or {}, "voice.pace_wpm") or 160
    hooks = cli.split_texts(paths.read_text(args.file), "lines")
    if not hooks:
        print("no hooks found (one per line; lines starting with # are ignored)")
        return 1
    ranked = score_hooks(hooks, ctx, wpm)

    if args.json:
        for r in ranked:
            if not args.detail:
                r.pop("detail")
        R.emit_json({"profile": prof, "wpm": wpm, "hooks": ranked})
        return 0

    print("HOOK RANKING  (%d hooks, %g wpm, profile: %s)" % (len(ranked), wpm, "yes" if prof else "none"))
    print("=" * 78)
    for i, r in enumerate(ranked):
        print("%s %5.1f %-6s %s" % ("->" if i == 0 else "  ", r["score"], r["band"], r["hook"]))
        meta = "        %.1fs to say" % r["seconds"]
        if r["too_long_to_say"]:
            meta += " (over %.0fs: cut words; aim for ~3s)" % HOOK_MAX_SECONDS
        meta += " | formula: %s | weakest: %s" % (", ".join(r["formulas"]) or "none", r["weakest"])
        print(meta)
        for d in r["dealbreakers"]:
            print("        dealbreaker: " + d)
        if args.detail:
            print(engine.render(r["detail"], show_limits=False))
            print()
    if not args.detail:
        print("\nWhy the top hook scored %.1f:" % ranked[0]["score"])
        print(engine.render(ranked[0]["detail"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
