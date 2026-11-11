import json
import os
import unittest

import helpers
from igkit import engine, features as F, paths


class TestRules(unittest.TestCase):
    def test_rule_math(self):
        rng = {"type": "range", "ideal": [5, 14], "zero_at": [1, 28]}
        self.assertEqual(engine.score_rule(rng, 9), 100.0)
        self.assertEqual(engine.score_rule(rng, 1), 0.0)
        self.assertEqual(engine.score_rule(rng, 3), 50.0)
        self.assertEqual(engine.score_rule(rng, 21), 50.0)
        mx = {"type": "max", "good": 0, "zero_at": 2}
        self.assertEqual(engine.score_rule(mx, 0), 100.0)
        self.assertEqual(engine.score_rule(mx, 1), 50.0)
        self.assertEqual(engine.score_rule(mx, 5), 0.0)
        mn = {"type": "min", "zero_at": 0, "good": 4}
        self.assertEqual(engine.score_rule(mn, 2), 50.0)
        self.assertEqual(engine.score_rule(mn, 9), 100.0)
        b = {"type": "bool", "true": 100, "false": 40}
        self.assertEqual(engine.score_rule(b, False), 40.0)
        self.assertIsNone(engine.score_rule(b, None))


class TestRubrics(unittest.TestCase):
    def test_all_rubrics_valid(self):
        names = engine.list_rubrics()
        self.assertEqual(set(names), {"hook", "caption", "originality", "storytelling", "engagement", "human", "comment", "dm", "bio"})
        for n in names:
            rb = engine.load_rubric(n)
            self.assertEqual(engine.check_rubric(rb), [], n)
            self.assertTrue(rb["limitations"], n)

    def test_invalid_rubric_is_rejected(self):
        bad = {"id": "x", "name": "X", "measures": "m", "limitations": [], "bands": {},
               "criteria": [{"id": "c", "weight": 1, "measures": "m",
                             "rules": [{"feature": "nope", "type": "max", "good": 0, "zero_at": 1}]}]}
        probs = engine.check_rubric(bad)
        self.assertTrue(any("unknown feature" in p for p in probs))
        self.assertTrue(any("no 'why'" in p for p in probs))

    def test_every_feature_runs_on_awkward_input(self):
        ctx = {"profile": helpers.fixture_profile(), "keywords": ["sourdough starter"], "refs": ["a b c d e"],
               "post": "starter", "formulas": paths.load_config("hook_formulas")["formulas"]}
        for text in ("", "🔥", "Hey.", "A " * 300):
            for name in F.FEATURES:
                F.compute(name, text, ctx)  # must not raise

    def test_unmeasured_rules_are_skipped_and_reported(self):
        res = engine.score("Great point about the rye flour.", "comment", {})
        crit = {c["id"]: c for c in res["criteria"]}
        self.assertIsNone(crit["specific"]["score"])
        self.assertLess(res["measured_share"], 1.0)
        self.assertIn("Partial score", engine.render(res))

    def test_dealbreaker_caps(self):
        res = engine.score("Hey guys, today I want to talk about sourdough", "hook", {})
        self.assertEqual(res["score"], 25.0)
        self.assertTrue(res["raw_score"] > res["score"])
        self.assertEqual(res["dealbreakers"][0]["id"], "greeting")

    def test_hook_ordering(self):
        ctx = {"profile": helpers.fixture_profile(), "formulas": paths.load_config("hook_formulas")["formulas"]}
        good = engine.score("Feeding your starter on a schedule is wrong for home bakers.", "hook", ctx)["score"]
        meh = engine.score("Sourdough is important.", "hook", ctx)["score"]
        bad = engine.score("Stop scrolling if you want to unlock your potential and elevate your baking", "hook", ctx)["score"]
        self.assertGreater(good, 80)
        self.assertLess(meh, 55)
        self.assertLess(bad, 50)

    def test_render_explains(self):
        res = engine.score("Sourdough is important.", "hook", {})
        out = engine.render(res)
        self.assertIn("HOOK STRENGTH", out)
        self.assertIn("Limit:", out)
        self.assertIn("fix:", out)

    def test_user_override_rubric(self):
        home = os.environ["IG_AGENT_HOME"]
        os.makedirs(os.path.join(home, "rubrics"), exist_ok=True)
        rb = engine.load_rubric("hook")
        rb["name"] = "Hook strength (custom)"
        path = os.path.join(home, "rubrics", "hook.json")
        with open(path, "w") as fh:
            json.dump(rb, fh)
        try:
            self.assertEqual(engine.load_rubric("hook")["name"], "Hook strength (custom)")
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
