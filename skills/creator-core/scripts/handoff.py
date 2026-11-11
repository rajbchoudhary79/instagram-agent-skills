#!/usr/bin/env python3
"""Handoff packets between skills.

  handoff.py new --from viral-researcher --to reel-creator --task "write 3 reels from the top formulas" > handoff.json
  handoff.py validate handoff.json
  handoff.py show handoff.json

A packet keeps three things apart as work moves through a pipeline: the payload
(what the next skill needs), what is verified (with a source), and what is
assumed. The receiving skill must not promote an assumption to a fact.
"""

import argparse
import datetime
import json
import sys

import _bootstrap  # noqa: F401
from igkit import paths, report as R, schema


def validate_packet(packet):
    errs = schema.validate(packet, paths.load_json(paths.config_path("handoff.schema.json")))
    if not errs and packet["from"] == packet["to"]:
        errs.append("$: from and to are the same skill")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    n = sub.add_parser("new")
    n.add_argument("--from", dest="src", required=True)
    n.add_argument("--to", dest="dst", required=True)
    n.add_argument("--task", required=True)
    n.add_argument("--topic", default="")
    v = sub.add_parser("validate")
    v.add_argument("file")
    s = sub.add_parser("show")
    s.add_argument("file")
    args = ap.parse_args(argv)

    if args.cmd == "new":
        pkt = {"from": args.src, "to": args.dst, "task": args.task, "topic": args.topic,
               "created": datetime.date.today().isoformat(), "payload": {}, "artifacts": [],
               "verified": [], "assumptions": [], "open_questions": [], "approval_required": True}
        errs = validate_packet(pkt)
        if errs:
            print("\n".join(errs), file=sys.stderr)
            return 1
        R.emit_json(pkt)
        return 0
    if args.cmd in ("validate", "show"):
        try:
            pkt = json.loads(paths.read_text(args.file))
        except ValueError as exc:
            print("INVALID: not JSON (%s)" % exc)
            return 1
        errs = validate_packet(pkt)
        if args.cmd == "validate":
            print("VALID" if not errs else "INVALID\n  " + "\n  ".join(errs))
            return 1 if errs else 0
        print("HANDOFF  %s -> %s" % (pkt.get("from"), pkt.get("to")))
        print("  task:        %s" % pkt.get("task"))
        print("  artifacts:   %d" % len(pkt.get("artifacts", [])))
        print("  verified:    " + ("; ".join(pkt.get("verified", [])) or "none"))
        print("  assumptions: " + ("; ".join(pkt.get("assumptions", [])) or "none"))
        for q in pkt.get("open_questions", []):
            print("  open:        " + q)
        if errs:
            print("  INVALID: " + "; ".join(errs))
        return 1 if errs else 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
