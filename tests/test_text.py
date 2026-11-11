import unittest

import helpers  # noqa: F401
from igkit import text as T


class TestText(unittest.TestCase):
    def test_words_and_numbers(self):
        self.assertEqual(T.word_count("I lost $18,000 on one contract."), 6)
        self.assertIn("$18,000", T.numbers("I lost $18,000 on one contract."))
        self.assertTrue(T.has_number("three loaves"))
        self.assertFalse(T.has_number("no digits here"))

    def test_sentences(self):
        s = T.sentences("One. Two words here! Three? \nFour")
        self.assertEqual(len(s), 4)

    def test_emoji_count_handles_zwj_and_skin_tones(self):
        self.assertEqual(T.emoji_count("🔥🔥"), 2)
        self.assertEqual(T.emoji_count("👨‍👩‍👧"), 1)
        self.assertEqual(T.emoji_count("👍🏽"), 1)
        self.assertEqual(T.emoji_count("plain"), 0)

    def test_hashtags_mentions_links_placeholders(self):
        t = "Read this #sourdough #bread_tips @priya.nair www.example.com {{amount}} and email a@b.com"
        self.assertEqual(T.hashtags(t), ["sourdough", "bread_tips"])
        self.assertEqual(T.mentions(t), ["priya.nair"])
        self.assertTrue(any("example.com" in link for link in T.links(t)))
        self.assertEqual(T.placeholders(t), ["{{amount}}"])

    def test_speech_seconds(self):
        short = T.speech_seconds("One price.", 160)
        longer = T.speech_seconds("One bowl, one jar, one tin, and one loaf by the evening.", 160)
        self.assertLess(short, longer)
        # numbers are spoken as several words
        self.assertGreater(T.spoken_word_count("$18,000"), 2)
        # explicit pauses add time
        self.assertAlmostEqual(T.speech_seconds("Wait (pause 1.5) now", 160) - T.speech_seconds("Wait now", 160), 1.5, places=1)

    def test_reading_seconds(self):
        self.assertEqual(T.reading_seconds(""), 0.0)
        self.assertEqual(T.reading_seconds("one two"), 1.0)
        self.assertGreater(T.reading_seconds(" ".join(["word"] * 14)), 3.5)

    def test_truncate_visible_cuts_on_word_boundary(self):
        text = "Your starter is not a pet. " * 10
        vis, cut = T.truncate_visible(text, 40)
        self.assertTrue(cut)
        self.assertLessEqual(len(vis), 40)
        self.assertFalse(vis.endswith(" "))
        self.assertTrue(text.startswith(vis))
        self.assertEqual(T.truncate_visible("short", 125), ("short", False))

    def test_rhythm_measures(self):
        self.assertIsNone(T.burstiness("One. Two."))
        uniform = "This sentence has six words. That sentence has six words. Every sentence has six words here."
        varied = "No. This one is a much longer sentence with plenty of words in it. Short again."
        self.assertLess(T.burstiness(uniform), T.burstiness(varied))
        self.assertIsNone(T.mattr("too short"))
        self.assertGreater(T.mattr("the quick brown fox jumps over the lazy dog and runs far away"), 0.7)

    def test_shingle_overlap(self):
        a = "feed the starter once and bake the loaf the next evening"
        self.assertIsNone(T.shingle_overlap(a, []))
        self.assertEqual(T.shingle_overlap(a, [a]), 1.0)
        self.assertLess(T.shingle_overlap(a, ["completely different words about cooking pasta at home tonight"]), 0.05)


if __name__ == "__main__":
    unittest.main()
