import json
import os
import tempfile
import unittest

import helpers
from igkit import paths, profile as P, schema


class TestProfile(unittest.TestCase):
    def test_fixture_is_valid_and_complete(self):
        data, path, errs = P.load(helpers.PROFILE)
        self.assertEqual(errs, [])
        pct, missing = P.completeness(data)
        self.assertGreaterEqual(pct, 95)

    def test_schema_catches_errors(self):
        data = helpers.fixture_profile()
        del data["audience"]["who"]
        data["voice"]["tone"] = "direct"
        data["voice"]["emoji_policy"] = "lots"
        errs = schema.validate(data, paths.load_json(paths.config_path("profile.schema.json")))
        joined = "\n".join(errs)
        self.assertIn("audience: missing required field 'who'", joined)
        self.assertIn("voice.tone: expected array", joined)
        self.assertIn("emoji_policy", joined)

    def test_template_only_misses_the_required_minimum(self):
        tpl = helpers.load_json(P.template_path())
        errs = schema.validate(tpl, paths.load_json(paths.config_path("profile.schema.json")))
        self.assertTrue(errs)
        for e in errs:
            self.assertIn("shorter than", e)
        pct, _ = P.completeness(tpl)
        self.assertLess(pct, 40)

    def test_resolution_order(self):
        tmp = tempfile.mkdtemp()
        explicit = os.path.join(tmp, "x.json")
        self.assertEqual(P.resolve_path(explicit), explicit)
        old = os.environ.get("IG_PROFILE")
        try:
            os.environ["IG_PROFILE"] = "/somewhere/p.json"
            self.assertEqual(P.resolve_path(), "/somewhere/p.json")
            del os.environ["IG_PROFILE"]
            self.assertEqual(P.resolve_path(), os.path.join(os.environ["IG_AGENT_HOME"], "profile.json"))
        finally:
            if old is not None:
                os.environ["IG_PROFILE"] = old

    def test_project_local_profile_is_found(self):
        tmp = tempfile.mkdtemp()
        local = os.path.join(tmp, ".creator-content-kit")
        os.makedirs(local)
        with open(os.path.join(local, "profile.json"), "w") as fh:
            fh.write("{}")
        sub = os.path.join(tmp, "a", "b")
        os.makedirs(sub)
        e = helpers.env(profile=None)
        e.pop("IG_AGENT_HOME")
        e["HOME"] = tempfile.mkdtemp()
        import subprocess
        import sys
        r = subprocess.run([sys.executable, os.path.join(helpers.CORE, "scripts", "profile.py"), "where"],
                           cwd=sub, env=e, capture_output=True, text=True)
        self.assertEqual(os.path.realpath(r.stdout.splitlines()[0]),
                         os.path.realpath(os.path.join(local, "profile.json")))

    def test_brief(self):
        data = helpers.fixture_profile()
        b = P.brief(data, helpers.PROFILE)
        self.assertIn("Priya Nair", b)
        self.assertIn("never invent", b)
        self.assertIn("STARTER", b)


class TestProfileCLI(unittest.TestCase):
    def test_missing_profile_exit_3(self):
        home = tempfile.mkdtemp()
        r = helpers.run("creator-core", ["scripts/profile.py", "show"], home=home, profile=None)
        self.assertEqual(r.returncode, 3)
        self.assertIn("NO PROFILE", r.stdout)

    def test_init_then_check(self):
        home = tempfile.mkdtemp()
        r = helpers.run("creator-core", ["scripts/profile.py", "init"], home=home, profile=None)
        self.assertEqual(r.returncode, 0, r.stderr)
        for f in ("profile.json", "voice.md", "brand.md", "audience.md", "content-strategy.md"):
            self.assertTrue(os.path.isfile(os.path.join(home, f)), f)
        r = helpers.run("creator-core", ["scripts/profile.py", "check"], home=home, profile=None)
        self.assertEqual(r.returncode, 1)  # empty template: required minimum not filled
        r2 = helpers.run("creator-core", ["scripts/profile.py", "init"], home=home, profile=None)
        self.assertIn("keep", r2.stdout)  # never overwrites without --force

    def test_show_section_and_json(self):
        out, r = helpers.run_json("creator-core", ["scripts/profile.py", "show", "--section", "goals.cta"])
        self.assertEqual(out["keyword"], "STARTER")
        out, r = helpers.run_json("creator-core", ["scripts/profile.py", "check", "--json"])
        self.assertTrue(out["valid"])

    def test_every_skill_can_read_the_profile(self):
        for s in helpers.skill_names():
            r = helpers.run(s, ["scripts/core.py", "profile", "show"])
            self.assertEqual(r.returncode, 0, "%s: %s" % (s, r.stderr))
            self.assertIn("Priya Nair", r.stdout, s)


if __name__ == "__main__":
    unittest.main()
