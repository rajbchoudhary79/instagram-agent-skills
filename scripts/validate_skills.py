#!/usr/bin/env python3
"""Validate every skill folder against the project's skill contract.

  python3 scripts/validate_skills.py            all skills
  python3 scripts/validate_skills.py reel-creator    one skill

Checks
  - SKILL.md exists with YAML frontmatter: name (== folder), description (<= 1024 chars,
    says when to use it)
  - the required sections are present, in any order
  - every file the SKILL.md points to (references/..., scripts/..., examples/..., *.json) exists
  - scripts/_bootstrap.py and scripts/core.py match the canonical shims
  - every script answers --help with exit code 0
  - examples/cases.json exists and parses
Exit 1 on any problem.
"""

import filecmp
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
SHIMS = os.path.join(SKILLS, "creator-core", "lib", "shims")

REQUIRED_SECTIONS = [
    ("When to use", r"^## When to use\b"),
    ("Inputs", r"^## Inputs\b"),
    ("Required inputs", r"^### Required\b"),
    ("Optional inputs", r"^### Optional\b"),
    ("Workflow", r"^## Workflow\b"),
    ("Decisions", r"^## Decisions\b"),
    ("Output format", r"^## Output format\b"),
    ("Quality checklist", r"^## Quality checklist\b"),
    ("Errors and edge cases", r"^## Errors and edge cases\b"),
    ("Examples", r"^## Examples\b"),
]
REF_RE = re.compile(r"`((?:\.\./[a-z][a-z-]*/)?(?:references|scripts|examples|config|templates)/[\w./-]+|[\w-]+\.json)`")


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return None, "no frontmatter"
    end = text.find("\n---", 4)
    if end < 0:
        return None, "frontmatter not closed"
    block = text[4:end]
    data = {}
    key = None
    for line in block.splitlines():
        m = re.match(r"^([a-z_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            data[key] = "" if val in (">-", "|", ">") else val
        elif key and line.startswith("  "):
            data[key] = (data[key] + " " + line.strip()).strip()
    return data, None


def check_skill(name, run_help=True):
    sdir = os.path.join(SKILLS, name)
    probs = []
    path = os.path.join(sdir, "SKILL.md")
    if not os.path.isfile(path):
        return ["missing SKILL.md"]
    text = open(path, encoding="utf-8").read()
    fm, err = parse_frontmatter(text)
    if err:
        return [err]
    if fm.get("name") != name:
        probs.append("frontmatter name %r != folder %r" % (fm.get("name"), name))
    desc = fm.get("description", "")
    if not desc:
        probs.append("empty description")
    elif len(desc) > 1024:
        probs.append("description is %d chars (max 1024)" % len(desc))
    elif not re.search(r"\buse when\b", desc, re.IGNORECASE):
        probs.append("description should say 'Use when ...'")
    for label, pat in REQUIRED_SECTIONS:
        if not re.search(pat, text, re.MULTILINE):
            probs.append("missing section: " + label)
    lines = text.count("\n")
    if lines > 260:
        probs.append("SKILL.md is %d lines; move detail into references/ (progressive disclosure)" % lines)
    for ref in sorted(set(REF_RE.findall(text))):
        target = os.path.normpath(os.path.join(sdir, ref))
        if ref.endswith(".json") and "/" not in ref:
            if not (os.path.isfile(target) or os.path.isfile(os.path.join(sdir, "examples", ref))):
                continue  # bare json names in prose (e.g. profile.json) are not file references
        if not os.path.exists(target) and "/" in ref:
            probs.append("referenced file missing: " + ref)
    sc = os.path.join(sdir, "scripts")
    for shim in ("_bootstrap.py", "core.py"):
        p = os.path.join(sc, shim)
        if not os.path.isfile(p) or not filecmp.cmp(p, os.path.join(SHIMS, shim), shallow=False):
            probs.append("scripts/%s missing or out of sync (run scripts/sync_shims.py)" % shim)
    cases = os.path.join(sdir, "examples", "cases.json")
    if not os.path.isfile(cases):
        probs.append("examples/cases.json missing")
    else:
        try:
            if not json.load(open(cases)).get("cases"):
                probs.append("examples/cases.json has no cases")
        except ValueError as exc:
            probs.append("examples/cases.json invalid: %s" % exc)
    if run_help and os.path.isdir(sc):
        for f in sorted(os.listdir(sc)):
            if f.endswith(".py") and not f.startswith("_") and f != "core.py":
                r = subprocess.run([sys.executable, os.path.join(sc, f), "--help"], capture_output=True, text=True, cwd=sdir)
                if r.returncode != 0:
                    probs.append("scripts/%s --help failed: %s" % (f, (r.stderr or r.stdout).strip()[-200:]))
    return probs


def skill_names():
    return sorted(d for d in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, d)) and not d.startswith(".") and os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def main():
    names = sys.argv[1:] or skill_names()
    bad = 0
    for n in names:
        probs = check_skill(n)
        print("%-14s %s" % (n, "ok" if not probs else "PROBLEMS"))
        for p in probs:
            print("    - " + p)
        bad += bool(probs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
