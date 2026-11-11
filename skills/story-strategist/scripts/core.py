#!/usr/bin/env python3
"""Run a shared creator-core tool from any skill.

  python3 scripts/core.py profile show          # read the creator profile
  python3 scripts/core.py score --rubric hook draft.txt
  python3 scripts/core.py gate draft.txt --type caption
  python3 scripts/core.py handoff validate handoff.json

An identical copy lives in every skill's scripts/ folder.
"""

import os
import runpy
import sys

import _bootstrap

TOOLS = ("profile", "score", "gate", "handoff", "claims")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in TOOLS:
        sys.stderr.write("usage: core.py {%s} [args...]\n" % "|".join(TOOLS))
        return 2
    script = os.path.join(_bootstrap.CORE_DIR, "scripts", sys.argv[1] + ".py")
    sys.argv = [script] + sys.argv[2:]
    runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
