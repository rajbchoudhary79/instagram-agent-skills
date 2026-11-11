"""Structure tests: every skill meets the SKILL.md contract and its tools respond."""

import os
import shutil
import sys
import tempfile
import unittest

import helpers

sys.path.insert(0, os.path.join(helpers.ROOT, "scripts"))
import validate_skills  # noqa: E402

EXPECTED = {"creator-core", "reel-creator", "viral-researcher", "caption-writer", "carousel-creator", "story-strategist", "profile-auditor", "content-planner",
            "content-humanizer", "comment-assistant", "reply-assistant", "dm-assistant", "content-repurposer", "performance-auditor"}


class TestSkills(unittest.TestCase):
    def test_all_thirteen_plus_core_exist(self):
        self.assertEqual(set(helpers.skill_names()), EXPECTED)

    def test_contract(self):
        for name in helpers.skill_names():
            self.assertEqual(validate_skills.check_skill(name, run_help=True), [], name)

    def test_shims_in_sync(self):
        r = helpers.run("creator-core", [os.path.join(helpers.ROOT, "scripts", "sync_shims.py"), "--check"], cwd=helpers.ROOT)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_every_skill_reads_profile_first(self):
        for name in helpers.skill_names():
            with open(os.path.join(helpers.SKILLS, name, "SKILL.md"), encoding="utf-8") as fh:
                text = fh.read()
            wf = text.split("## Workflow", 1)[1]
            self.assertIn("profile", wf.split("\n2.", 1)[0].lower() + wf[:600].lower(), name)

    def test_no_detector_bypass_or_virality_promises(self):
        bad = ("undetectable", "bypass ai detect", "guaranteed viral", "guarantee virality", "will go viral")
        for name in helpers.skill_names():
            with open(os.path.join(helpers.SKILLS, name, "SKILL.md"), encoding="utf-8") as fh:
                text = fh.read().lower()
            for phrase in bad:
                for line in text.splitlines():
                    if phrase in line:
                        self.assertTrue(any(w in line for w in ("never", "not", "no ", "bad", "do not", "never claim", '"')),
                                        "%s: %r used affirmatively: %s" % (name, phrase, line))

    def test_validator_catches_a_broken_skill(self):
        tmp = tempfile.mkdtemp()
        old = validate_skills.SKILLS
        try:
            os.makedirs(os.path.join(tmp, "broken-skill", "scripts"))
            with open(os.path.join(tmp, "broken-skill", "SKILL.md"), "w") as fh:
                fh.write("---\nname: wrong-name\ndescription: does things\n---\n\n# x\n\n## Workflow\nSee `references/missing.md`.\n")
            validate_skills.SKILLS = tmp
            probs = "\n".join(validate_skills.check_skill("broken-skill", run_help=False))
            self.assertIn("frontmatter name", probs)
            self.assertIn("Use when", probs)
            self.assertIn("missing section: Quality checklist", probs)
            self.assertIn("referenced file missing: references/missing.md", probs)
            self.assertIn("out of sync", probs)
        finally:
            validate_skills.SKILLS = old
            shutil.rmtree(tmp)

    def test_skills_never_reference_passwords_except_to_refuse(self):
        for name in helpers.skill_names():
            for root, _, files in os.walk(os.path.join(helpers.SKILLS, name)):
                for f in files:
                    if f.endswith((".md", ".py")):
                        with open(os.path.join(root, f), encoding="utf-8") as fh:
                            text = fh.read().lower()
                        heading = ""
                        for line in text.splitlines():
                            if line.startswith("#"):
                                heading = line
                            if "password" in line:
                                context = line + " " + heading  # a bullet under "What it never does" is a refusal
                                self.assertTrue(any(w in context for w in ("never", "not", "no ", "refus", "won't")),
                                                "%s/%s: %s" % (name, f, line))


if __name__ == "__main__":
    unittest.main()
