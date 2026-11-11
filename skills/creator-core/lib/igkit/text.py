"""Text primitives. Deterministic, standard library only.

Everything here is a heuristic. Word and sentence splitting is tuned for
English social copy and degrades gracefully on other Latin-script languages.
"""

import math
import re
import statistics

TOKEN_RE = re.compile(r"[$€£₹]?\d(?:[\d,.:]*\d)?[%a-zA-Z]*|[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
NUMBER_RE = re.compile(r"[$€£₹]?\d[\d,.:]*\s?(?:%|k|K|m|M|x|X)?")
_UNITS = "one two three four five six seven eight nine"
_TEENS = "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen"
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety"
_SCALE = "hundred thousand million billion half dozen couple"
NUMBER_WORDS = frozenset(" ".join((_UNITS, _TEENS, _TENS, _SCALE)).split())
HASHTAG_RE = re.compile(r"(?<![\w&])#([^\W_][\w]*)", re.UNICODE)
MENTION_RE = re.compile(r"(?<![\w.])@([A-Za-z0-9_.]{1,30})")
# Bare domains are only treated as links for TLDs creators commonly put in captions,
# so "end.Next" or "e.g." never count.
_LINK_TLDS = sorted("ai app co com dev gg info io link ly me net org shop store".split(), key=len, reverse=True)
LINK_RE = re.compile(
    r"\b(?:https?://|www\.)\S+|\b[a-z0-9-]+\.(?:%s)(?:/\S*)?\b" % "|".join(_LINK_TLDS),
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])[\"'”’)]*\s+|\n+")

_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),
    (0x2600, 0x27BF),
    (0x2B00, 0x2BFF),
    (0x1F1E6, 0x1F1FF),
    (0x2300, 0x23FF),
)
_ZWJ = 0x200D
_VS16 = 0xFE0F


def is_emoji_char(ch):
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _EMOJI_RANGES)


def emoji_count(text):
    """Count emoji glyphs, treating ZWJ sequences and skin-tone modifiers as one."""
    count = 0
    prev_zwj = False
    for ch in text:
        cp = ord(ch)
        if cp == _ZWJ:
            prev_zwj = True
            continue
        if cp == _VS16 or 0x1F3FB <= cp <= 0x1F3FF:
            continue
        if is_emoji_char(ch):
            if not prev_zwj:
                count += 1
        prev_zwj = False
    return count


def strip_emoji(text):
    return "".join(ch for ch in text if not is_emoji_char(ch) and ord(ch) not in (_ZWJ, _VS16))


def words(text):
    return TOKEN_RE.findall(text)


def word_count(text):
    return len(words(text))


def lower_words(text):
    return [w.lower() for w in words(text)]


def sentences(text):
    parts = [p.strip() for p in SENTENCE_SPLIT_RE.split(text)]
    return [p for p in parts if p and words(p)]


def lines(text):
    return [ln for ln in text.splitlines() if ln.strip()]


def first_line(text):
    for ln in text.splitlines():
        if ln.strip():
            return ln.strip()
    return ""


def hashtags(text):
    return HASHTAG_RE.findall(text)


def mentions(text):
    return MENTION_RE.findall(text)


def links(text):
    return LINK_RE.findall(text)


def placeholders(text):
    return PLACEHOLDER_RE.findall(text)


def numbers(text):
    return [m.group(0).strip() for m in NUMBER_RE.finditer(text) if re.search(r"\d", m.group(0))]


def has_number(text):
    if numbers(text):
        return True
    return any(w in NUMBER_WORDS for w in lower_words(text))


def sentence_lengths(text):
    return [word_count(s) for s in sentences(text)]


def burstiness(text):
    """Coefficient of variation of sentence length. None when fewer than 3 sentences."""
    lens = sentence_lengths(text)
    if len(lens) < 3:
        return None
    mean = statistics.mean(lens)
    if mean == 0:
        return None
    return statistics.pstdev(lens) / mean


def mattr(text, window=50):
    """Moving-average type-token ratio. Length-robust lexical diversity, 0..1."""
    toks = lower_words(text)
    if len(toks) < 10:
        return None
    if len(toks) <= window:
        return len(set(toks)) / len(toks)
    ratios = [len(set(toks[i:i + window])) / window for i in range(len(toks) - window + 1)]
    return sum(ratios) / len(ratios)


def ngrams(tokens, n):
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def repeated_ngram_ratio(text, n=3):
    """Share of word n-grams that occur more than once. None for short texts."""
    toks = lower_words(text)
    grams = ngrams(toks, n)
    if len(grams) < 10:
        return None
    counts = {}
    for g in grams:
        counts[g] = counts.get(g, 0) + 1
    repeated = sum(c for c in counts.values() if c > 1)
    return repeated / len(grams)


def repeated_opener_share(text):
    """Largest share of sentences that start with the same word. None under 4 sentences."""
    sents = sentences(text)
    if len(sents) < 4:
        return None
    firsts = {}
    for s in sents:
        w = lower_words(s)
        if w:
            firsts[w[0]] = firsts.get(w[0], 0) + 1
    return max(firsts.values()) / len(sents)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def shingle_overlap(text, refs, n=4):
    """Highest n-gram Jaccard overlap between text and any reference text. None without refs."""
    if not refs:
        return None
    mine = set(ngrams(lower_words(text), n))
    if not mine:
        return 0.0
    return max(jaccard(mine, set(ngrams(lower_words(r), n))) for r in refs)


def spoken_word_count(text):
    """Words as spoken aloud: '$18,000' reads as 'eighteen thousand dollars'."""
    total = 0
    for tok in words(text):
        if re.match(r"[$€£₹]?\d", tok):
            digits = re.sub(r"\D", "", tok)
            spoken = max(1, math.ceil(len(digits) / 2))
            if tok[0] in "$€£₹":
                spoken += 1
            if tok.endswith("%"):
                spoken += 1
            total += spoken
        else:
            total += 1
    return total


PAUSE_RE = re.compile(r"\(pause\s*([\d.]+)?\s*s?\)", re.IGNORECASE)


def speech_seconds(text, wpm=160.0):
    """Estimated seconds to say text aloud at wpm, with punctuation pauses."""
    explicit = 0.0
    for m in PAUSE_RE.finditer(text):
        explicit += float(m.group(1)) if m.group(1) else 0.5
    clean = PAUSE_RE.sub(" ", text)
    seconds = spoken_word_count(clean) / (wpm / 60.0)
    seconds += 0.15 * len(re.findall(r"[,;:]", clean))
    seconds += 0.3 * len(re.findall(r"[.!?…](?=\s|$)", clean))
    return round(seconds + explicit, 2)


def reading_seconds(text, wps=3.5):
    """Seconds an average viewer needs to read on-screen text (about 3.5 words/second, min 1s)."""
    n = word_count(text)
    if n == 0:
        return 0.0
    return round(max(1.0, n / wps), 2)


def starts_with_emoji(text):
    s = text.lstrip()
    return bool(s) and is_emoji_char(s[0])


def truncate_visible(text, limit):
    """What the feed shows before '... more': the first limit chars, cut at a word boundary,
    and never past the first double line break region (approximation)."""
    if len(text) <= limit:
        return text, False
    cut = text[:limit]
    if " " in cut and not text[limit].isspace():
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(), True
