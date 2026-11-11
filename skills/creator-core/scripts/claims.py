#!/usr/bin/env python3
"""List every factual claim in a draft and whether the creator profile verifies it.

  claims.py draft.txt
  claims.py draft.txt --json

A claim is a metric ($, %, 'N clients'), an achievement ('I grew', 'we helped'),
a credential ('award-winning', 'featured in') or a quoted testimonial. Verified
means it matches an entry in profile.verified_facts. Exit 1 when any claim is
unverified.
"""

import argparse
import sys

import _bootstrap  # noqa: F401
from igkit import claims as C, cli, paths, report as R


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    cli.add_common(ap, keywords=False)
    args = ap.parse_args(argv)
    ctx, prof = cli.build_ctx(args)
    text = paths.read_text(args.file)
    found = C.find_claims(text)
    rows = [dict(c, verified=C.is_verified(c, ctx.get("profile"))) for c in found]
    if args.json:
        R.emit_json({"profile": prof, "claims": rows})
    else:
        if not rows:
            print("No claims found.")
        else:
            print(R.table([("yes" if r["verified"] else "NO", r["type"], r["match"], r["sentence"][:50]) for r in rows],
                          ["verified", "type", "claim", "sentence"]))
        if prof is None:
            print("\n(no creator profile: nothing can be verified)")
    return 1 if any(not r["verified"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
