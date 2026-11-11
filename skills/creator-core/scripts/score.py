#!/usr/bin/env python3
"""Score text against a JSON rubric and explain the score.

  score.py --rubric hook draft.txt
  score.py --rubric hook hooks.txt --split lines        rank several options
  score.py --rubric comment reply.txt --post post.txt
  score.py --rubric originality draft.txt --refs inspo1.txt inspo2.txt
  score.py --list                                        available rubrics
  score.py --rubric hook - < draft.txt                   read stdin

Rubrics: config/rubrics/*.json, or ~/.creator-content-kit/rubrics/<name>.json to
override, or a path to any rubric file. Scores are heuristics, never a
prediction of reach.
"""

import argparse
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, paths, report as R


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="text file, or - for stdin")
    ap.add_argument("--rubric", help="rubric name or path")
    ap.add_argument("--split", choices=["none", "lines", "blocks"], default="none",
                    help="score several texts from one file")
    ap.add_argument("--list", action="store_true", help="list rubrics")
    ap.add_argument("--quiet-limits", action="store_true", help="omit the limitations footer")
    cli.add_common(ap, refs=True, post=True)
    args = ap.parse_args(argv)

    if args.list:
        for name in engine.list_rubrics():
            rb = engine.load_rubric(name)
            print("%-13s %s" % (name, rb["measures"]))
        return 0
    if not args.rubric or not args.file:
        ap.error("--rubric and a file are required (or --list)")

    rubric = engine.load_rubric(args.rubric)
    ctx, prof = cli.build_ctx(args)
    if args.rubric == "hook" or rubric["id"] == "hook":
        ctx["formulas"] = paths.load_config("hook_formulas")["formulas"]
    texts = cli.split_texts(paths.read_text(args.file), args.split)
    results = [dict(engine.score(t, rubric, ctx), text=t) for t in texts]
    ranked = sorted(results, key=lambda r: r["score"], reverse=True)

    if args.json:
        R.emit_json({"rubric": rubric["id"], "profile": prof, "keywords": ctx.get("keywords"),
                     "results": ranked if len(ranked) > 1 else ranked[0]})
        return 0

    if len(ranked) > 1:
        print("%s RANKING  (%d options)" % (rubric["name"].upper(), len(ranked)))
        print("=" * 78)
        for i, r in enumerate(ranked):
            arrow = "->" if i == 0 else "  "
            print("%s %5.1f %-6s %s" % (arrow, r["score"], r["band"], r["text"][:60] + ("..." if len(r["text"]) > 60 else "")))
            if r["weakest"]:
                print("            weakest: %s" % r["weakest"])
            for d in r["dealbreakers"]:
                print("            dealbreaker: %s" % d["message"])
        print()
        print("Detail for the top option:")
        print(engine.render(ranked[0], show_limits=not args.quiet_limits))
    else:
        print(engine.render(ranked[0], show_limits=not args.quiet_limits))
    if prof is None and not args.no_profile:
        print("  (no creator profile found; audience checks skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
