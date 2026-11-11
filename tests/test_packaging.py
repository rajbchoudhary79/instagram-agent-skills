"""Install paths: packaged zips are self-contained; side-by-side installs work; the scaffold passes validation."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

import helpers

sys.path.insert(0, os.path.join(helpers.ROOT, "scripts"))
import new_skill  # noqa: E402
import package  # noqa: E402
import validate_skills  # noqa: E402


class TestPackaging(unittest.TestCase):
    def test_zip_runs_without_sibling_core(self):
        out = tempfile.mkdtemp()
        path = package.package("caption-writer", out)
        dest = tempfile.mkdtemp()
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            self.assertIn("caption-writer/SKILL.md", names)
            self.assertIn("caption-writer/_core/lib/igkit/engine.py", names)
            self.assertIn("caption-writer/_core/scripts/gate.py", names)
            self.assertFalse(any("__pycache__" in n for n in names))
            zf.extractall(dest)
        sdir = os.path.join(dest, "caption-writer")
        r = subprocess.run([sys.executable, "scripts/caption_lint.py", "examples/good-caption.txt"], cwd=sdir,
                           env=helpers.env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run([sys.executable, "scripts/core.py", "gate", "examples/good-caption.txt", "--type", "caption"],
                           cwd=sdir, env=helpers.env(), capture_output=True, text=True)
        self.assertIn("VERDICT", r.stdout, r.stderr)

    def test_missing_core_is_a_clear_error(self):
        dest = tempfile.mkdtemp()
        shutil.copytree(os.path.join(helpers.SKILLS, "reel-creator"), os.path.join(dest, "reel-creator"))
        r = subprocess.run([sys.executable, "scripts/hook_rank.py", "--formulas"], cwd=os.path.join(dest, "reel-creator"),
                           env=helpers.env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("creator-core not found", r.stderr)

    def test_install_script_side_by_side(self):
        dest = tempfile.mkdtemp()
        r = subprocess.run(["sh", os.path.join(helpers.ROOT, "scripts", "install.sh"), "--dest", dest],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(set(os.listdir(dest)), set(helpers.skill_names()))
        r = subprocess.run([sys.executable, os.path.join(dest, "reel-creator", "scripts", "hook_rank.py"), "--formulas"],
                           env=helpers.env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_scaffold_passes_validation(self):
        tmp = tempfile.mkdtemp()
        os.symlink(os.path.join(helpers.SKILLS, "creator-core"), os.path.join(tmp, "creator-core"))
        old = (new_skill.SKILLS, validate_skills.SKILLS)
        argv = sys.argv
        try:
            new_skill.SKILLS = validate_skills.SKILLS = tmp
            sys.argv = ["new_skill.py", "collab-scout", "Find and pitch collaboration partners"]
            self.assertEqual(new_skill.main(), 0)
            self.assertEqual(validate_skills.check_skill("collab-scout"), [])
            r = subprocess.run([sys.executable, "scripts/tool.py", "examples/good.txt", "--json"],
                               cwd=os.path.join(tmp, "collab-scout"), env=helpers.env(), capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            new_skill.SKILLS, validate_skills.SKILLS = old
            sys.argv = argv
            shutil.rmtree(tmp)


class TestSafety(unittest.TestCase):
    def test_no_network_code(self):
        banned = ("import socket", "import urllib", "from urllib", "import requests", "http.client", "import ftplib",
                  "import smtplib", "webbrowser")
        for root, _, files in os.walk(helpers.ROOT):
            if "/tests" in root or "/dist" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(root, f), encoding="utf-8") as fh:
                        text = fh.read()
                    for b in banned:
                        self.assertNotIn(b, text, os.path.join(root, f))

    def test_standard_library_only(self):
        import ast
        allowed = set(sys.stdlib_module_names) | {"igkit", "_bootstrap", "helpers", "validate_skills", "new_skill", "package"}
        for root, _, files in os.walk(helpers.SKILLS):
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(root, f), encoding="utf-8") as fh:
                        tree = ast.parse(fh.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            mods = [a.name.split(".")[0] for a in node.names]
                        elif isinstance(node, ast.ImportFrom) and node.level == 0:
                            mods = [node.module.split(".")[0]]
                        else:
                            continue
                        for m in mods:
                            self.assertIn(m, allowed, "%s imports %s" % (f, m))


if __name__ == "__main__":
    unittest.main()
