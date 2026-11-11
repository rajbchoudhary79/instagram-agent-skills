#!/usr/bin/env python3
"""DM templates and the DM checker.

  dm.py templates                                   list skeletons and when each is allowed
  dm.py render collab_pitch --var first_name=Sam --var ...   fill a skeleton (refuses if any {{slot}} is empty)
  dm.py lint draft.txt --kind collab --post their_post.txt
  dm.py lint draft.txt --kind followup --followup 3
  dm.py lint draft.txt --kind keyword --automated --they-messaged-first --hours-since 30

--kind: keyword | first | reply | lead | collab | followup
Policy checks: follow-up count (max 2), links in a first message, automation
only when they messaged first and inside the 24-hour window. Quality checks:
the dm rubric (personal, brief, one question, no pressure, no placeholders).
Exit 0 READY, 1 REVIEW, 2 BLOCKED. Nothing is ever sent by this tool.
"""

import argparse
import os
import re
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, lexicon as L, paths, report as R, text as T

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOT_RE = re.compile(r"\{\{([a-z_]+)\}\}")


def templates():
    return paths.load_json(os.path.join(HERE, "templates.json"))


def render(tid, values):
    tpl = templates()["templates"].get(tid)
    if not tpl:
        raise KeyError("no template '%s'" % tid)
    slots = SLOT_RE.findall(tpl["body"])
    missing = [s for s in dict.fromkeys(slots) if not values.get(s, "").strip()]
    if missing:
        return None, missing
    return SLOT_RE.sub(lambda m: values[m.group(1)].strip(), tpl["body"]), []


def lint(text, kind, ctx, followup=None, automated=False, they_first=False, hours_since=None):
    rules = templates()["rules"]
    plat = paths.load_config("platform")["messaging"]
    window = plat["api_standard_window_hours"]["value"]
    checks = []

    def add(level, cid, msg):
        checks.append({"level": level, "id": cid, "message": msg})

    if followup is not None and followup > rules["max_followups"]:
        add("FAIL", "followups", "Follow-up #%d. Two is the limit; after that, stop." % followup)
    if automated and not they_first:
        add("FAIL", "automation", "Automated message to someone who has not messaged, commented or replied first. Not allowed.")
    if automated and hours_since is not None and hours_since > window:
        add("FAIL", "window", "%gh since their last message; automated replies need to be inside the %dh window." % (hours_since, window))
    if automated and kind != "keyword":
        add("WARN", "automation_kind", "Only keyword deliveries are suited to automation. Write the rest by hand.")
    links = T.links(text)
    if links and kind in ("first", "collab", "followup"):
        add("WARN", "link", "Link in a %s message. Ask first; send the link when they say yes." % kind)
    if kind == "keyword" and not links and not T.placeholders(text):
        add("WARN", "delivery", "Keyword delivery with no link or attachment. Deliver what they asked for in the first message.")
    ph = T.placeholders(text)
    if ph:
        add("FAIL", "placeholders", "Unfilled placeholder(s): %s." % ", ".join(sorted(set(ph))))
    if L.invisible_chars(text):
        add("FAIL", "invisible", "Invisible characters.")
    if L.count_terms(text, "spam_markers"):
        add("FAIL", "spam", "Spam markers present.")
    res = engine.score(text, "dm", ctx)
    thr = 70
    add("PASS" if res["score"] >= thr else "WARN", "rubric", "DM quality %.0f (weakest: %s)." % (res["score"], res["weakest"]))
    for d in res["dealbreakers"]:
        add("WARN", "dealbreaker", d["message"])
    if kind == "collab" and ctx.get("post") is None:
        add("INFO", "context", "No --post given, so personalisation was not measured. A collab pitch must reference their work.")
    return {"checks": checks, "verdict": R.verdict(checks), "score": res}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("templates")
    r = sub.add_parser("render")
    r.add_argument("template")
    r.add_argument("--var", action="append", default=[], help="slot=value (repeat)")
    lt = sub.add_parser("lint")
    lt.add_argument("file")
    lt.add_argument("--kind", default="reply", choices=["keyword", "first", "reply", "lead", "collab", "followup"])
    lt.add_argument("--followup", type=int, help="which follow-up this is (1, 2, ...)")
    lt.add_argument("--automated", action="store_true", help="will be sent by an automation tool")
    lt.add_argument("--they-messaged-first", action="store_true")
    lt.add_argument("--hours-since", type=float, help="hours since their last message")
    cli.add_common(lt, keywords=False, post=True)
    args = ap.parse_args(argv)

    if args.cmd == "templates":
        t = templates()
        for tid, v in t["templates"].items():
            print("%-22s %s%s" % (tid, v["trigger"], "  [automatable]" if v["automatable"] else ""))
        print("\nRules: %s" % t["rules"]["automation"])
        return 0
    if args.cmd == "render":
        vals = dict(v.split("=", 1) for v in args.var if "=" in v)
        try:
            text, missing = render(args.template, vals)
        except KeyError as exc:
            print(exc)
            return 2
        if missing:
            print("REFUSED: fill every slot first. Missing: " + ", ".join(missing))
            return 2
        print(text)
        return 0
    if args.cmd == "lint":
        ctx, prof = cli.build_ctx(args, use_profile_keywords=False)
        res = lint(paths.read_text(args.file), args.kind, ctx, args.followup, args.automated,
                   args.they_messaged_first, args.hours_since)
        if args.json:
            R.emit_json({"verdict": res["verdict"], "checks": res["checks"], "score": res["score"]["score"]})
        else:
            print("DM CHECK  kind=%s" % args.kind)
            print("=" * 78)
            print(R.render_checks(res["checks"]))
            print("VERDICT: %s  (nothing has been sent)" % res["verdict"])
        return {"READY": 0, "REVIEW": 1, "BLOCKED": 2}[res["verdict"]]
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
