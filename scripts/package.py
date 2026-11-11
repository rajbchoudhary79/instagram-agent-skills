#!/usr/bin/env python3
"""Build self-contained zip files, one per skill, for environments that upload
skills one at a time (e.g. claude.ai Settings > Capabilities > Skills).

  python3 scripts/package.py                 all skills -> dist/<skill>.zip
  python3 scripts/package.py reel-creator caption-writer
  python3 scripts/package.py --out /tmp/dist

Each zip contains the skill folder plus creator-core's lib/, config/, templates/ and scripts/
vendored under <skill>/_core/, so its scripts work without a sibling creator-core.
(creator-core itself is packaged as-is.)
"""

import argparse
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
CORE = os.path.join(SKILLS, "creator-core")
SKIP_DIRS = {"__pycache__", ".pytest_cache", "_core"}
SKIP_EXT = (".pyc",)


def add_tree(zf, src, arc_prefix):
    for base, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f.endswith(SKIP_EXT) or f == ".DS_Store":
                continue
            full = os.path.join(base, f)
            zf.write(full, os.path.join(arc_prefix, os.path.relpath(full, src)))


def package(name, out_dir):
    sdir = os.path.join(SKILLS, name)
    if not os.path.isfile(os.path.join(sdir, "SKILL.md")):
        raise SystemExit("not a skill: %s" % name)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name + ".zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        add_tree(zf, sdir, name)
        if name != "creator-core":
            for part in ("lib", "config", "templates", "scripts"):
                add_tree(zf, os.path.join(CORE, part), os.path.join(name, "_core", part))
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skills", nargs="*")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    args = ap.parse_args(argv)
    names = args.skills or sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))
    for n in names:
        p = package(n, args.out)
        print("%-14s %s (%d KB)" % (n, p, os.path.getsize(p) // 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
