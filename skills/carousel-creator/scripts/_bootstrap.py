"""Find the shared creator-core library and put it on sys.path.

An identical copy of this file lives in every skill's scripts/ folder
(kept in sync by scripts/sync_shims.py at the repo root). It looks for creator-core:
  1. $IG_CORE_DIR
  2. <skill>/_core            (a packaged, self-contained skill)
  3. <skill> itself           (when this is creator-core)
  4. <skill>/../creator-core       (skills installed side by side, or a plugin)
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)


def _find_core():
    cands = []
    if os.environ.get("IG_CORE_DIR"):
        cands.append(os.environ["IG_CORE_DIR"])
    cands += [os.path.join(SKILL_DIR, "_core"), SKILL_DIR, os.path.join(os.path.dirname(SKILL_DIR), "creator-core")]
    for c in cands:
        if os.path.isfile(os.path.join(c, "lib", "igkit", "__init__.py")):
            return os.path.abspath(c)
    sys.stderr.write(
        "creator-core not found. Install the creator-core skill next to this skill "
        "(same skills/ folder), or set IG_CORE_DIR.\n"
    )
    sys.exit(2)


CORE_DIR = _find_core()
_LIB = os.path.join(CORE_DIR, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
