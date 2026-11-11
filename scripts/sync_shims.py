#!/usr/bin/env python3
"""Copy the canonical shims (skills/creator-core/lib/shims/*.py) into every skill's scripts/ folder.

  python3 scripts/sync_shims.py          write
  python3 scripts/sync_shims.py --check  exit 1 if any copy is out of date
"""

import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
SHIMS = os.path.join(SKILLS, "creator-core", "lib", "shims")


def main():
    check = "--check" in sys.argv
    stale = []
    for skill in sorted(os.listdir(SKILLS)):
        sdir = os.path.join(SKILLS, skill)
        if not os.path.isfile(os.path.join(sdir, "SKILL.md")):
            continue
        os.makedirs(os.path.join(sdir, "scripts"), exist_ok=True)
        for shim in sorted(os.listdir(SHIMS)):
            if not shim.endswith(".py"):
                continue
            src = os.path.join(SHIMS, shim)
            dst = os.path.join(sdir, "scripts", shim)
            if os.path.isfile(dst) and filecmp.cmp(src, dst, shallow=False):
                continue
            stale.append(dst)
            if not check:
                shutil.copyfile(src, dst)
                if shim == "core.py":
                    os.chmod(dst, 0o755)
    if check:
        for s in stale:
            print("out of date: " + os.path.relpath(s, ROOT))
        return 1 if stale else 0
    print("synced %d file(s)" % len(stale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
