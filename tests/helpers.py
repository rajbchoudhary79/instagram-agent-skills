"""Shared test helpers. Standard library only (unittest)."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
CORE = os.path.join(SKILLS, "creator-core")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
PROFILE = os.path.join(FIXTURES, "profile.json")

# Isolate in-process library calls from the developer's own ~/.creator-content-kit.
_HOME = tempfile.mkdtemp(prefix="cck-test-home-")
os.environ["IG_AGENT_HOME"] = _HOME
os.environ["IG_PROFILE"] = PROFILE
os.environ.pop("IG_CORE_DIR", None)

if os.path.join(CORE, "lib") not in sys.path:
    sys.path.insert(0, os.path.join(CORE, "lib"))


def fixture_profile():
    with open(PROFILE, encoding="utf-8") as fh:
        return json.load(fh)


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def skill_names():
    return sorted(d for d in os.listdir(SKILLS) if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def env(home=None, profile=PROFILE):
    e = dict(os.environ)
    e["IG_AGENT_HOME"] = home or tempfile.mkdtemp(prefix="cck-test-")
    if profile:
        e["IG_PROFILE"] = profile
    else:
        e.pop("IG_PROFILE", None)
    e.pop("IG_CORE_DIR", None)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return e


def run(skill, args, home=None, profile=PROFILE, stdin=None, cwd=None):
    """Run a command inside a skill folder. args[0] is a script path relative to the skill."""
    return subprocess.run([sys.executable] + list(args), cwd=cwd or os.path.join(SKILLS, skill),
                          env=env(home, profile), capture_output=True, text=True, input=stdin)


def run_json(skill, args, **kw):
    r = run(skill, args, **kw)
    try:
        return json.loads(r.stdout), r
    except ValueError:
        raise AssertionError("not JSON (exit %s):\nSTDOUT:\n%s\nSTDERR:\n%s" % (r.returncode, r.stdout[-2000:], r.stderr[-2000:]))


def load_script(skill, name):
    """Import a skill script as a module (its scripts/ dir goes on sys.path for _bootstrap)."""
    sdir = os.path.join(SKILLS, skill, "scripts")
    if sdir not in sys.path:
        sys.path.insert(0, sdir)
    mod_name = "igtest_%s_%s" % (skill.replace("-", "_"), name)
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(sdir, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_tmp(text, suffix=".txt"):
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="cck-test-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def get_path(obj, path):
    """Dotted path lookup; integers index lists (negative allowed); '' returns obj."""
    if path == "":
        return obj
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur
