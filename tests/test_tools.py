"""Unit tests for each skill's Python utility."""

import datetime as dt
import json
import os
import tempfile
import unittest
import xml.dom.minidom

import helpers
from igkit import paths


class TestCaption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("caption-writer", "caption_lint")

    def ids(self, text, ctx=None):
        return {c["id"]: c["level"] for c in self.m.lint(text, ctx or {})["checks"]}

    def test_limits(self):
        self.assertEqual(self.ids("x" * 2300)["length"], "FAIL")
        tags = " ".join("#tag%d" % i for i in range(7))
        self.assertEqual(self.ids("Line one.\n\n" + tags)["hashtag_count"], "FAIL")
        self.assertEqual(self.ids("Line one.\n\n#one #two")["hashtag_count"], "PASS")

    def test_first_line_rules(self):
        self.assertEqual(self.ids("Hey guys! Here's my take.")["greeting"], "FAIL")
        self.assertEqual(self.ids("#sourdough is hard")["hashtag_first"], "FAIL")
        self.assertEqual(self.ids("🔥 Sourdough is hard")["emoji_first"], "WARN")
        self.assertEqual(self.ids("A" * 200 + " end")["first_line_cut"], "WARN")

    def test_asks_links_keywords(self):
        ids = self.ids("Read this.\nwww.mysite.com\nComment YES and save this and follow me")
        self.assertEqual(ids["link"], "WARN")
        self.assertEqual(ids["many_asks"], "WARN")
        ids = self.ids("Sourdough starter made simple. Comment STARTER.", {"keywords": ["sourdough starter", "sourdough schedule"]})
        self.assertEqual(ids["keywords"], "WARN")
        self.assertEqual(ids["ask"], "PASS")

    def test_preview_window(self):
        res = self.m.lint("word " * 100, {}, window=50)
        self.assertTrue(res["truncated"])
        self.assertLessEqual(len(res["visible"]), 50)


class TestBeats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("reel-creator", "script_timer")

    def test_parse_annotations(self):
        b = self.m.parse("# note\nHOOK: One price. [text: 1 price] [visual: desk] [cut]\n[hold: 2] [visual: b-roll]\n")
        self.assertEqual(len(b), 2)
        self.assertEqual(b[0]["label"], "HOOK")
        self.assertEqual(b[0]["spoken"], "One price.")
        self.assertEqual(b[0]["on_screen"], ["1 price"])
        self.assertEqual(b[0]["visual"], ["desk"])
        self.assertEqual(b[0]["edit"], ["cut"])
        self.assertEqual(b[1]["hold"], 2.0)

    def test_timing_and_flags(self):
        beats = self.m.parse("HOOK: " + "word " * 20 + "\nStatic line " + "talking " * 25 + "\nCTA: Comment WORD.")
        total = self.m.time_beats(beats, 160, self.m.DEFAULTS)
        self.assertAlmostEqual(total, beats[-1]["end"])
        self.assertEqual(beats[1]["start"], beats[0]["end"])
        msgs = " ".join(f["message"] for f in self.m.flag(beats, total, 60, self.m.DEFAULTS))
        self.assertIn("Hook takes", msgs)
        self.assertIn("no on-screen text", msgs.lower())
        self.assertIn("no visual change", msgs)
        self.assertIn("target", msgs)

    def test_silent_beat_gets_hold(self):
        beats = self.m.parse("[visual: product shot] [hold: 1.5]")
        self.m.time_beats(beats, 160, self.m.DEFAULTS)
        self.assertEqual(beats[0]["seconds"], 1.5)


class TestHookscore(unittest.TestCase):
    def test_ranking_and_timing(self):
        m = helpers.load_script("reel-creator", "hook_rank")
        ranked = m.score_hooks(["Sourdough is important.", "Nobody tells home bakers the fridge does most of the work."], {}, 160)
        self.assertEqual(ranked[0]["formulas"], ["hard_way"])
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])
        self.assertIn("seconds", ranked[0])


class TestResearchLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("viral-researcher", "research_log")

    def test_parse_num(self):
        self.assertEqual(self.m.parse_num("12.3K"), 12300)
        self.assertEqual(self.m.parse_num("1.2M"), 1200000)
        self.assertEqual(self.m.parse_num("4,512"), 4512)
        self.assertIsNone(self.m.parse_num(""))
        self.assertIsNone(self.m.parse_num("n/a"))

    def test_derived_baseline_needs_five_posts(self):
        rows = [{"url": str(i), "account": "a", "format": "reel", "hook": "x", "topic": None, "views": v,
                 "likes": None, "comments": None, "shares": None, "saves": None, "posted": None,
                 "account_median_views": None, "followers": None, "source": "manual", "notes": None}
                for i, v in enumerate([1000, 1000, 1000, 1000, 5000])]
        res = self.m.analyse(rows)
        self.assertEqual(res["summary"]["ranked"], 5)
        self.assertEqual(res["ranked"][0]["multiple"], 5.0)
        self.assertTrue(res["ranked"][0]["baseline_source"].startswith("derived"))
        res4 = self.m.analyse([dict(r) for r in rows[:4]])
        self.assertEqual(res4["summary"]["ranked"], 0)  # never estimated from too little data

    def test_missing_metrics_stay_missing(self):
        rows = self.m.load_rows(os.path.join(helpers.SKILLS, "viral-researcher", "examples", "observations.csv"))
        res = self.m.analyse(rows)
        for r in res["ranked"] + res["unranked"]:
            if r["saves"] is None:
                self.assertIn("saves", r["missing"])
        md = self.m.to_markdown(res, "test")
        self.assertIn("not independently verified", md)


class TestTriage(unittest.TestCase):
    def test_classify(self):
        m = helpers.load_script("reply-assistant", "triage")
        cats = helpers.load_json(os.path.join(helpers.SKILLS, "reply-assistant", "categories.json"))["categories"]
        cases = {
            "How much is the workshop?": "lead",
            "STARTER": "keyword",
            "starter please": "keyword",
            "How much is the starter guide?": "lead",
            "I didn't get the download": "support",
            "Promote it on @growthpage": "spam",
            "what about rye flour?": "question",
            "This is bad advice": "pushback",
            "🔥🔥": "praise",
            "@friend @other": "tag",
        }
        for text, want in cases.items():
            self.assertEqual(m.classify(text, cats, "STARTER")[0], want, text)


class TestPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("content-planner", "planner")

    def test_round_robin_hits_shares_without_clumping(self):
        seq = self.m.smooth_round_robin({"a": 0.5, "b": 0.3, "c": 0.2}, 10)
        self.assertEqual(seq.count("a"), 5)
        self.assertEqual(seq.count("b"), 3)
        self.assertEqual(seq.count("c"), 2)
        self.assertFalse(any(seq[i] == seq[i + 1] == seq[i + 2] for i in range(len(seq) - 2)))

    def test_slot_dates(self):
        d = self.m.slot_dates(dt.date(2026, 11, 16), dt.date(2026, 11, 29), 3, ["mon", "wed", "fri", "sun"])
        self.assertEqual(len(d), 6)
        self.assertTrue(all(x.strftime("%a").lower()[:3] in ("mon", "wed", "fri", "sun") for x in d))

    def test_full_cycle(self):
        cal = os.path.join(tempfile.mkdtemp(), "calendar.json")
        r = helpers.run("content-planner", ["scripts/planner.py", "--file", cal, "plan", "--month", "2026-12"])
        self.assertEqual(r.returncode, 0, r.stderr)
        items = helpers.load_json(cal)["items"]
        self.assertEqual(len(items), 18)  # 4 posting days a week in December 2026, minus none past the 31st
        helpers.run("content-planner", ["scripts/planner.py", "--file", cal, "idea", "add", "Overnight fridge proof"])
        helpers.run("content-planner", ["scripts/planner.py", "--file", cal, "idea", "use", "i-0001", items[0]["id"]])
        helpers.run("content-planner", ["scripts/planner.py", "--file", cal, "status", items[0]["id"], "approved"])
        data = helpers.load_json(cal)
        first = next(i for i in data["items"] if i["id"] == items[0]["id"])
        self.assertEqual(first["topic"], "Overnight fridge proof")
        self.assertEqual([h["status"] for h in first["history"]], ["slot", "planned", "approved"])
        self.assertEqual(data["ideas"], [])
        bad = helpers.run("content-planner", ["scripts/planner.py", "--file", cal, "status", items[0]["id"], "posted-ish"])
        self.assertNotEqual(bad.returncode, 0)
        out = os.path.join(tempfile.mkdtemp(), "c.csv")
        helpers.run("content-planner", ["scripts/planner.py", "--file", cal, "export", "--csv", out])
        with open(out, encoding="utf-8") as fh:
            self.assertEqual(len(fh.read().strip().splitlines()), 19)


class TestHumanize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("content-humanizer", "rewrite_check")

    def test_clean(self):
        out, log = self.m.clean("One​ price only — always. 2020–2024 work. Family 👨‍👩‍👧")
        self.assertNotIn("​", out)
        self.assertNotIn(" ", out)
        self.assertNotIn("—", out)
        self.assertIn("2020-2024", out)
        self.assertIn("👨‍👩‍👧", out)  # emoji sequence untouched
        self.assertTrue(any("zero width space" in x for x in log))
        kept, _ = self.m.clean("a — b", dashes="keep")
        self.assertIn("—", kept)

    def test_findings_and_voice_check(self):
        f = self.m.findings("Let's dive in.\nIt might perhaps work — or not.", helpers.fixture_profile())
        kinds = {x["kind"] for x in f}
        self.assertTrue({"slop", "hedge", "dash"} <= kinds)
        self.assertEqual([x["line"] for x in f if x["kind"] == "slop"], [1])
        v = self.m.voice_check("Here's the move: feed it twice, then wait.", "Leverage synergy to unlock value.", helpers.fixture_profile())
        self.assertIn("here's the move", v["own_phrases_lost"])
        self.assertTrue(v["notes"])


class TestCarousel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("carousel-creator", "carousel")

    def test_validate_limits(self):
        checks, _ = self.m.validate({"slides": [{"role": "cover", "headline": "One"}]}, {})
        self.assertTrue(any(c["id"] == "count" and c["level"] == "FAIL" for c in checks))
        slides = [{"role": "cover", "headline": "Stop feeding your starter at night"}] + \
                 [{"role": "point", "headline": "Point %d" % i, "body": "flour water starter"} for i in range(21)]
        checks, _ = self.m.validate({"slides": slides}, {})
        self.assertTrue(any(c["id"] == "count" and c["level"] == "FAIL" for c in checks))

    def test_svg_is_valid_xml(self):
        theme = self.m.theme_for({}, helpers.fixture_profile())
        self.assertEqual(theme["bg"], "#F5F1EA")
        svg, overflow = self.m.render_svg({"headline": "Fish & chips <script>", "body": "A & B"}, 1, 3, theme, self.m.rules())
        xml.dom.minidom.parseString(svg)
        self.assertFalse(overflow)
        _, overflow = self.m.render_svg({"headline": "x", "body": "word " * 400}, 2, 3, theme, self.m.rules())
        self.assertTrue(overflow)


class TestStory(unittest.TestCase):
    def test_funnel_rules(self):
        m = helpers.load_script("story-strategist", "story")
        seq = {"frames": [{"purpose": "hook", "type": "video"},
                          {"purpose": "convert", "type": "text", "sticker": {"type": "link", "url": "https://x.y"}},
                          {"purpose": "interact", "type": "text", "sticker": {"type": "poll", "options": ["a", "b"]}}]}
        ids = {c["id"] for c in m.validate(seq)}
        self.assertIn("funnel", ids)
        seq["frames"][1], seq["frames"][2] = seq["frames"][2], seq["frames"][1]
        ids = {c["id"] for c in m.validate(seq)}
        self.assertNotIn("funnel", ids)


class TestProfileAudit(unittest.TestCase):
    def test_username_and_pending(self):
        m = helpers.load_script("profile-auditor", "profile_audit")
        res = m.audit({"username": "priya.nair_bakes2019", "bio": ""}, helpers.fixture_profile())
        crit = {c["id"]: c for c in res["criteria"]}
        self.assertLess(crit["username"]["got"], 3)
        self.assertEqual(set(res["pending"]), {"photo", "positioning", "consistency"})
        self.assertEqual(res["out_of"], 74)


class TestDM(unittest.TestCase):
    def test_render_and_policy(self):
        m = helpers.load_script("dm-assistant", "dm")
        text, missing = m.render("lead_followup_2", {"first_name": "Sam", "close_the_loop_kindly": "No pressure at all."})
        self.assertEqual(missing, [])
        self.assertIn("Sam", text)
        res = m.lint("Hey Sam, sent it over. What will you use it for?", "keyword", {}, automated=True, they_first=True, hours_since=30)
        self.assertIn("window", {c["id"] for c in res["checks"]})
        res = m.lint("Hey Sam, sent it over: https://x.y/t. What will you use it for?", "keyword", {}, automated=True, they_first=True, hours_since=2)
        self.assertEqual(res["verdict"], "READY")


class TestSegment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = helpers.load_script("content-repurposer", "segment")

    def test_parse_formats(self):
        vtt = "WEBVTT\n\n00:01.000 --> 00:04.500\nHello <b>there</b>.\n\n00:04.500 --> 00:09.000\nSecond line.\n"
        cues, timed = self.m.parse(vtt)
        self.assertTrue(timed)
        self.assertEqual(cues[0]["start"], 1.0)
        self.assertEqual(cues[0]["text"], "Hello there.")
        cues, timed = self.m.parse("First sentence here. Second one follows.")
        self.assertFalse(timed)
        self.assertEqual(len(cues), 2)
        self.assertGreater(cues[1]["start"], 0)
        self.assertEqual(self.m._ts("01:02:03,500"), 3723.5)


class TestAudit(unittest.TestCase):
    def test_rates_and_missing(self):
        m = helpers.load_script("performance-auditor", "audit")
        self.assertEqual(m.num("1.5K"), 1500)
        self.assertEqual(m.num("0:45"), 45)
        self.assertIsNone(m.num("--"))
        csvp = helpers.write_tmp("Post type,Reach,Saves,Description\nReel,1000,10,One\nCarousel,2000,60,Two\n", ".csv")
        rows = m.load(csvp)
        denom, med = m.enrich(rows)
        self.assertEqual(denom, "reach")
        self.assertAlmostEqual(rows[1]["saves_per_reach"], 0.03)
        self.assertIsNone(rows[0]["shares_per_reach"])
        self.assertIsNone(rows[0]["watch_ratio"])
        cov = m.coverage(rows)
        self.assertEqual(cov["shares"], 0)


class TestGate(unittest.TestCase):
    def test_gate_levels(self):
        m = helpers.load_script("creator-core", "gate")
        prof = helpers.fixture_profile()
        res = m.run_gate("Your starter is hungry, not dead. Comment STARTER.\n", "caption", {"profile": prof})
        self.assertIn(res["verdict"], ("READY", "REVIEW"))
        res = m.run_gate("Stop the hustle. Comment STARTER.", "caption", {"profile": prof})
        self.assertEqual(res["verdict"], "BLOCKED")
        res = m.run_gate("It cost me {{amount}}.", "caption", {"profile": prof})
        self.assertIn("placeholders", {c["id"] for c in res["checks"]})
        self.assertEqual(m.spoken("HOOK: Hi there [text: x]\n# note\nLine two [cut]"), "Hi there \nLine two ")


if __name__ == "__main__":
    unittest.main()
