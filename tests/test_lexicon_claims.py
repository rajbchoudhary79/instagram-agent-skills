import json
import unittest

import helpers
from igkit import claims as C
from igkit import lexicon as L


class TestLexicon(unittest.TestCase):
    def test_slop_and_tells(self):
        hits = dict(L.slop_hits("Let's dive in and unlock your potential."))
        self.assertIn("let's dive in", hits)
        self.assertIn("unlock your potential", hits)
        self.assertEqual(L.slop_hits("Send one price."), [])
        # curly apostrophes must not hide template constructions
        self.assertTrue(L.tells("Sourdough is not just bread — it’s a lifestyle."))
        self.assertTrue(L.tells("Here's the thing: nobody reads page 3."))
        self.assertFalse(L.tells("Put the price next to the outcome."))

    def test_invisible_chars(self):
        found = L.invisible_chars("price​ here now")
        codes = {c for _, c, _ in found}
        self.assertEqual(codes, {"200B", "00A0"})
        # emoji sequences use ZWJ / VS16 legitimately
        self.assertEqual(L.invisible_chars("family 👨‍👩‍👧 love ❤️"), [])

    def test_generic_comment(self):
        for c in ("Great post!", "🔥🔥🔥", "so true", "Love this, thanks for sharing!"):
            self.assertTrue(L.is_generic_comment(c), c)
        self.assertFalse(L.is_generic_comment("Did a colder fridge change your proof time?"))

    def test_asks(self):
        self.assertEqual(L.asks("Comment STARTER and I'll send it."), ["comment"])
        self.assertEqual(L.asks("Get the free checklist ↓"), ["book"])  # the profile auditor's own suggested wording
        self.assertEqual(L.asks("Get the dough in the fridge by six."), [])
        self.assertEqual(L.asks("comment if you want it"), [])  # keyword must be typeable: uppercase, quoted or 'below'
        self.assertIn("comment", L.asks("Comment below which one you use."))
        self.assertEqual(sorted(L.asks("Comment YES, save this and follow me for more")), ["comment", "follow", "save"])
        self.assertIn("dm", L.asks("DM me GUIDE for the template"))

    def test_starts_with(self):
        self.assertTrue(L.starts_with_any("Hey guys, quick one", "greetings"))
        self.assertFalse(L.starts_with_any("Heyday baking is over", "greetings"))
        self.assertTrue(L.starts_with_any("So today I want to", "filler_openers"))


class TestClaims(unittest.TestCase):
    def setUp(self):
        self.profile = helpers.fixture_profile()

    def test_finds_claim_types(self):
        found = C.find_claims('My workshop sign-ups went up 40%. I made $50,000 more. Award-winning baker. "Best teacher ever" - Sam')
        types = {c["type"] for c in found}
        self.assertEqual(types, {"metric", "achievement", "credential", "testimonial"})
        self.assertIn("$50,000", [c["match"] for c in found])  # not "$50,000 m"

    def test_placeholders_are_not_claims(self):
        self.assertEqual(C.find_claims("It cost me {{amount}} in 2024."), [])

    def test_verification_against_profile(self):
        self.assertEqual(C.unverified_claims("I raised my workshop price from $35 to $60.", self.profile), [])
        bad = C.unverified_claims("I raised my workshop price from $35 to $90.", self.profile)
        matches = [c["match"] for c in bad]
        self.assertIn("$90", matches)
        self.assertNotIn("$35", matches)
        self.assertTrue(C.unverified_claims("I made $50,000 last year.", None))

    def test_digit_subsets_do_not_verify(self):
        # "2" must not be verified just because "220" is in a fact
        self.assertTrue(C.unverified_claims("I grew to 2 million followers.", self.profile))


if __name__ == "__main__":
    unittest.main()
