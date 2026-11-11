#!/usr/bin/env python3
"""The shared creator profile.

  profile.py where                      which profile.json would be used
  profile.py init [--dir DIR] [--force] create profile.json + the .md companions
  profile.py check [--json]             validate and score completeness
  profile.py show [--json] [--section voice]
                                        the brief every skill reads before writing

Global: --profile PATH to use a specific file. Env: IG_PROFILE, IG_AGENT_HOME.
Exit codes: 0 ok, 1 invalid profile, 3 no profile found.
"""

import argparse
import os
import shutil
import sys

import _bootstrap  # noqa: F401
from igkit import paths, profile as P, report as R


def cmd_where(args):
    p = P.resolve_path(args.profile)
    print(p)
    print("exists" if os.path.isfile(p) else "missing (run: profile.py init)")
    return 0


def cmd_init(args):
    folder = os.path.abspath(os.path.expanduser(args.dir)) if args.dir else paths.data_home()
    os.makedirs(folder, exist_ok=True)
    created = []
    tdir = os.path.join(paths.CORE_DIR, "templates")
    for name in ("profile.json",) + P.COMPANIONS:
        dst = os.path.join(folder, name)
        if os.path.exists(dst) and not args.force:
            print("keep     %s (exists; --force to overwrite)" % dst)
            continue
        shutil.copyfile(os.path.join(tdir, name), dst)
        created.append(dst)
        print("created  %s" % dst)
    print("\nNext: fill profile.json (or ask the agent to interview you), then run profile.py check.")
    return 0


def _load_or_exit(args):
    data, path, errs = P.load(args.profile)
    if data is None:
        print("NO PROFILE: %s" % errs[0])
        print("Create one: python3 scripts/profile.py init   (or ask the agent to set it up)")
        sys.exit(3)
    return data, path, errs


def cmd_check(args):
    data, path, errs = _load_or_exit(args)
    pct, missing = P.completeness(data)
    if args.json:
        R.emit_json({"path": path, "valid": not errs, "errors": errs, "completeness": pct,
                     "missing": [{"field": f, "used_for": w} for f, w in missing],
                     "companions": P.companions(path)})
        return 1 if errs else 0
    print("PROFILE CHECK  %s" % path)
    print("  schema:        %s" % ("valid" if not errs else "INVALID"))
    for e in errs:
        print("    - " + e)
    print("  completeness:  %d%%  %s" % (pct, R.bar(pct)))
    for f, why in missing:
        print("    missing %-28s used for: %s" % (f, why))
    comp = P.companions(path)
    print("  companions:    %s" % (", ".join(os.path.basename(c) for c in comp) or "none"))
    if not (data.get("voice") or {}).get("sample_texts"):
        print("  tip: paste 3 real captions or transcripts into voice.sample_texts. Nothing improves voice match more.")
    return 1 if errs else 0


def cmd_show(args):
    data, path, errs = _load_or_exit(args)
    if args.section:
        sect = P.get(data, args.section)
        if sect is None:
            print("no section '%s'" % args.section)
            return 1
        R.emit_json(sect)
        return 0
    if args.json:
        R.emit_json(data)
        return 0
    print(P.brief(data, path))
    if errs:
        print("  WARNING: profile has schema errors; run profile.py check")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", help="path to a specific profile.json")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("where")
    i = sub.add_parser("init")
    i.add_argument("--dir")
    i.add_argument("--force", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--json", action="store_true")
    s = sub.add_parser("show")
    s.add_argument("--json", action="store_true")
    s.add_argument("--section", help="dotted path, e.g. voice or goals.cta")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2
    return {"where": cmd_where, "init": cmd_init, "check": cmd_check, "show": cmd_show}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
