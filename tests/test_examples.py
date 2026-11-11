"""Output-consistency tests: run every skill's examples/cases.json.

Each case runs a command inside the skill folder (with the fixture creator
profile and an empty temporary data home shared by that skill's cases, so
stateful tools like the planner can be exercised in order) and checks the exit
code and/or values in the JSON output.

Ops: == != < <= > >= between in contains len nonempty any_id none_id any_kind any_message any_contains
"""

import os
import tempfile
import unittest

import helpers


def check(op, actual, value):
    if op == "==":
        return actual == value
    if op == "!=":
        return actual != value
    if op == "<":
        return actual is not None and actual < value
    if op == "<=":
        return actual is not None and actual <= value
    if op == ">":
        return actual is not None and actual > value
    if op == ">=":
        return actual is not None and actual >= value
    if op == "between":
        return actual is not None and value[0] <= actual <= value[1]
    if op == "in":
        return actual in value
    if op == "contains":
        return value in actual
    if op == "len":
        return len(actual) == value
    if op == "nonempty":
        return bool(actual)
    if op == "any_id":
        return any(x.get("id") == value for x in actual)
    if op == "none_id":
        return not any(x.get("id") == value for x in actual)
    if op == "any_kind":
        return any(x.get("kind") == value for x in actual)
    if op == "any_message":
        return any(value in x.get("message", "") for x in actual)
    if op == "any_contains":
        return any(value in x for x in actual)
    raise ValueError("unknown op " + op)


class TestExamples(unittest.TestCase):
    def test_cases(self):
        total = 0
        for skill in helpers.skill_names():
            cases = helpers.load_json(os.path.join(helpers.SKILLS, skill, "examples", "cases.json"))["cases"]
            home = tempfile.mkdtemp(prefix="cck-cases-%s-" % skill)
            for case in cases:
                total += 1
                with self.subTest(skill=skill, case=case["name"]):
                    r = helpers.run(skill, case["run"], home=home)
                    if "exit" in case:
                        self.assertEqual(r.returncode, case["exit"], "%s\n%s\n%s" % (case["name"], r.stdout[-1500:], r.stderr[-1500:]))
                    elif not case.get("expect"):
                        self.assertEqual(r.returncode, 0, r.stderr)
                    if case.get("expect"):
                        import json
                        try:
                            out = json.loads(r.stdout)
                        except ValueError:
                            self.fail("%s: output is not JSON:\n%s\n%s" % (case["name"], r.stdout[-1500:], r.stderr[-1500:]))
                        for exp in case["expect"]:
                            actual = helpers.get_path(out, exp["path"])
                            self.assertTrue(check(exp["op"], actual, exp.get("value")),
                                            "%s: %s %s %r (actual %r)" % (case["name"], exp["path"], exp["op"], exp.get("value"), actual))
        self.assertGreaterEqual(total, 30)


if __name__ == "__main__":
    unittest.main()
