"""Where things live.

CORE_DIR    the creator-core folder (or the _core folder vendored into a packaged skill)
CONFIG_DIR  CORE_DIR/config: rubrics, lexicon, platform limits, schemas
data_home() the creator's own files: profile, calendar, research logs.
            $IG_AGENT_HOME, else ~/.creator-content-kit
"""

import json
import os

CORE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(CORE_DIR, "config")
LOCAL_DIRNAME = ".creator-content-kit"


def config_path(*parts):
    return os.path.join(CONFIG_DIR, *parts)


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_config(name):
    """Load CONFIG_DIR/<name>.json, letting a user override in data_home()/config/<name>.json."""
    override = os.path.join(data_home(), "config", name + ".json")
    if os.path.isfile(override):
        return load_json(override)
    return load_json(config_path(name + ".json"))


def data_home():
    env = os.environ.get("IG_AGENT_HOME")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(os.path.expanduser("~"), LOCAL_DIRNAME)


def find_local_dir(start=None):
    """Walk up from start (default cwd) looking for a project-local .creator-content-kit folder."""
    cur = os.path.abspath(start or os.getcwd())
    while True:
        cand = os.path.join(cur, LOCAL_DIRNAME)
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def workspace_dir():
    """Project-local .creator-content-kit if one exists above cwd, else data_home()."""
    if os.environ.get("IG_AGENT_HOME"):
        return data_home()
    return find_local_dir() or data_home()


def read_text(path):
    """Read a file, or stdin when path is '-'."""
    import sys
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()
