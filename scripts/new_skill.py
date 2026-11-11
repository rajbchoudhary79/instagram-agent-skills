#!/usr/bin/env python3
"""Scaffold a new skill that follows the project contract.

  python3 scripts/new_skill.py collab-scout "Find and pitch collaboration partners"

Creates skills/<name>/ with SKILL.md (all required sections), references/,
examples/cases.json, scripts/ with the shared shims and a starter tool that
already reads the creator profile and uses the scoring engine. Then run:

  python3 scripts/validate_skills.py <name>
  python3 -m unittest discover -s tests
"""

import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
SHIMS = os.path.join(SKILLS, "creator-core", "lib", "shims")

SKILL_MD = """---
name: {name}
description: >-
  {purpose}. Use when the user says "<trigger phrase 1>", "<trigger phrase 2>",
  or <situation that should activate this skill>.
---

# {name}

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- <situation>
- Not for: <neighbouring job> (<other skill>).

## Inputs

### Required
- <input>

### Optional
- <input>

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`. No profile: ask niche, audience, tone, language; label as assumptions.
2. <step>
3. **Check.** `python3 scripts/tool.py draft.txt`, then `python3 scripts/core.py gate draft.txt --type generic`.
4. **Deliver.** Copy-ready output. Nothing is posted or sent.

## Decisions

- <when X, do Y, because Z>

## Output format

```
<exact shape of the output>
```

## Quality checklist

- [ ] Profile read.
- [ ] No invented facts; unknowns are {{{{placeholders}}}}.
- [ ] Gate run; verdict shown.

## Errors and edge cases

- <failure> : <what to do>

## Examples

Good: <short example and why>.
Bad: <short example and why>.

## References

- `references/guide.md`: <what is in it>.
"""

TOOL = '''#!/usr/bin/env python3
"""Starter tool for {name}. Replace with the skill's own checks.

  tool.py draft.txt [--json]
"""

import argparse
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, paths, report as R


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    cli.add_common(ap)
    args = ap.parse_args(argv)
    ctx, prof = cli.build_ctx(args)
    text = paths.read_text(args.file)
    res = engine.score(text, "human", ctx)
    if args.json:
        R.emit_json({{"profile": prof, "human": res}})
    else:
        print(engine.render(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    name, purpose = sys.argv[1], sys.argv[2].rstrip(".")
    if not re.match(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$", name):
        print("name must be lowercase words joined by hyphens, e.g. collab-scout")
        return 2
    sdir = os.path.join(SKILLS, name)
    if os.path.exists(sdir):
        print("%s already exists" % sdir)
        return 1
    for sub in ("scripts", "references", "examples"):
        os.makedirs(os.path.join(sdir, sub))
    with open(os.path.join(sdir, "SKILL.md"), "w") as fh:
        fh.write(SKILL_MD.format(name=name, purpose=purpose))
    with open(os.path.join(sdir, "references", "guide.md"), "w") as fh:
        fh.write("# %s guide\n\nLonger reference material goes here, loaded only when needed.\n" % name)
    with open(os.path.join(sdir, "scripts", "tool.py"), "w") as fh:
        fh.write(TOOL.format(name=name))
    for shim in ("_bootstrap.py", "core.py"):
        shutil.copyfile(os.path.join(SHIMS, shim), os.path.join(sdir, "scripts", shim))
    for f in ("tool.py", "core.py"):
        os.chmod(os.path.join(sdir, "scripts", f), 0o755)
    with open(os.path.join(sdir, "examples", "good.txt"), "w") as fh:
        fh.write("Replace with an example of good output.\n")
    with open(os.path.join(sdir, "examples", "cases.json"), "w") as fh:
        json.dump({"cases": [{"name": "starter tool runs", "run": ["scripts/tool.py", "examples/good.txt", "--json"],
                              "exit": 0, "expect": [{"path": "human.score", "op": ">=", "value": 0}]}]}, fh, indent=2)
    print("created %s" % sdir)
    print("next: edit SKILL.md, then python3 scripts/validate_skills.py %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
