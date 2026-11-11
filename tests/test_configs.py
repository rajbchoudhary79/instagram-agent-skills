import glob
import json
import os
import re
import unittest

import helpers
from igkit import engine, paths, schema


class TestConfigs(unittest.TestCase):
    def test_every_json_file_parses(self):
        files = [f for f in glob.glob(os.path.join(helpers.ROOT, "**", "*.json"), recursive=True)
                 if "/dist/" not in f and "/node_modules/" not in f]
        self.assertGreater(len(files), 30)
        for f in files:
            with open(f, encoding="utf-8") as fh:
                json.load(fh)

    def test_platform_entries_have_confidence(self):
        plat = paths.load_config("platform")
        for section, entries in plat.items():
            if section.startswith("_") or not isinstance(entries, dict):
                continue
            if "value" in entries:
                entries = {section: entries}
            for k, v in entries.items():
                self.assertIn("value", v, "%s.%s" % (section, k))
                self.assertIn(v["confidence"], ("high", "medium", "verify"), "%s.%s" % (section, k))

    def test_hook_library(self):
        lib = paths.load_config("hook_formulas")
        ids = [f["id"] for f in lib["formulas"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 20)
        for f in lib["formulas"]:
            self.assertIn(f["family"], lib["families"], f["id"])
            for key in ("name", "template", "example", "on_screen", "use_for", "avoid_when", "match"):
                self.assertTrue(f[key], "%s.%s" % (f["id"], key))
            self.assertRegex(f["example"], re.compile(f["match"], re.IGNORECASE), "example must match its own formula: " + f["id"])

    def test_proof_examples_use_placeholders_not_invented_numbers(self):
        lib = paths.load_config("hook_formulas")
        for f in lib["formulas"]:
            if f["family"] == "proof":
                self.assertIn("{{", f["example"], f["id"])

    def test_lexicon_patterns_compile(self):
        lex = paths.load_config("lexicon")
        for t in lex["tells"]:
            re.compile(t["pattern"])
        for k, p in lex["cta_patterns"].items():
            if not k.startswith("_"):
                re.compile(p)
        for k, v in lex.items():
            if isinstance(v, list) and v and isinstance(v[0], str):
                self.assertEqual(len(v), len(set(v)), "duplicates in " + k)

    def test_gate_types_reference_real_rubrics(self):
        gate = paths.load_config("gate")
        names = set(engine.list_rubrics())
        for t, cfg in gate["types"].items():
            for r in list(cfg.get("rubrics", {})) + list(cfg.get("first_line", {})):
                self.assertIn(r, names, t)

    def test_handoff_schema_and_example(self):
        sch = paths.load_json(paths.config_path("handoff.schema.json"))
        ex = helpers.load_json(os.path.join(helpers.CORE, "examples", "handoff-example.json"))
        self.assertEqual(schema.validate(ex, sch), [])
        self.assertTrue(schema.validate({"from": "Not A Skill"}, sch))

    def test_skill_configs(self):
        S = helpers.SKILLS
        rub = helpers.load_json(os.path.join(S, "profile-auditor", "profile_rubric.json"))
        self.assertEqual(sum(c["points"] for c in rub["criteria"]), 100)
        mix = helpers.load_json(os.path.join(S, "content-planner", "mix.json"))
        self.assertAlmostEqual(sum(mix["mix"].values()), 1.0)
        for c in helpers.load_json(os.path.join(S, "reply-assistant", "categories.json"))["categories"]:
            for p in c["patterns"]:
                re.compile(p)
        st = helpers.load_json(os.path.join(S, "story-strategist", "stickers.json"))
        for s in st["interactive"]:
            self.assertIn(s, st["stickers"])
        tpl = helpers.load_json(os.path.join(S, "dm-assistant", "templates.json"))
        for tid, t in tpl["templates"].items():
            self.assertRegex(t["body"], r"\{\{[a-z_]+\}\}", tid)
            self.assertIn("trigger", t)
        car = helpers.load_json(os.path.join(S, "carousel-creator", "carousel.json"))
        self.assertIn("cta", car["roles"])

    def test_profile_fixture_matches_schema(self):
        sch = paths.load_json(paths.config_path("profile.schema.json"))
        self.assertEqual(schema.validate(helpers.fixture_profile(), sch), [])


if __name__ == "__main__":
    unittest.main()
