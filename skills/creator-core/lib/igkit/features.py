"""Named, measurable text features. Rubrics refer to these by name.

Every feature is f(text, ctx) -> number | bool | None.
None means "not measurable here" (too short, or the context it needs was not
given). The engine skips None rules and says so, instead of guessing.

ctx keys (all optional):
  profile   the creator profile dict
  keywords  list of search phrases the copy should contain
  refs      list of reference texts to check overlap against
  formulas  hook formula list (from config/hook_formulas.json)
  post      the text of the post being commented on / replied to
  visible   visible-window size in characters (captions)
"""

import re

from . import claims as C
from . import lexicon as L
from . import text as T

STOP = set("""a an the and or but if of to in on at for with from by as is are was were be been it its it's
this that these those i you he she we they me my your our their them his her not no so do does did
have has had just than then there here what when where who why how all any some can will would
should could about into over out up down very really more most too also only own same such""".split())

TRIAD_RE = re.compile(r"\b[\w'’-]+(?: [\w'’-]+){0,2}, [\w'’-]+(?: [\w'’-]+){0,2},? (?:and|or) [\w'’-]+", re.IGNORECASE)
NUMBERED_LINE_RE = re.compile(r"^\s*(?:\d{1,2}[.)]|[0-9]️?⃣|[•\-*→])\s+", re.MULTILINE)
PROPER_RE = re.compile(r"(?<=[a-z,;:] )[A-Z][a-z]{2,}")


def _per100(count, text):
    n = T.word_count(text)
    return None if n == 0 else 100.0 * count / n


def _profile_terms(profile, *paths):
    out = []
    for path in paths:
        node = profile or {}
        for key in path.split("."):
            node = node.get(key, {}) if isinstance(node, dict) else {}
        if isinstance(node, str) and node.strip():
            out.append(node.strip())
        elif isinstance(node, list):
            out.extend(str(x).strip() for x in node if str(x).strip())
    return out


def specificity_hits(text, ctx=None):
    nums = len(T.numbers(text)) + sum(1 for w in T.lower_words(text) if w in T.NUMBER_WORDS)
    units = L.count_terms(text, "concrete_units")
    proper = len(PROPER_RE.findall(text))
    return nums + units + proper


def keyword_coverage(text, ctx):
    kws = [k.strip().lower() for k in (ctx or {}).get("keywords") or [] if k.strip()]
    if not kws:
        return None
    low = text.lower()
    return sum(1 for k in kws if k in low) / len(kws)


def keyword_in_visible(text, ctx):
    kws = [k.strip().lower() for k in (ctx or {}).get("keywords") or [] if k.strip()]
    if not kws:
        return None
    vis, _ = T.truncate_visible(text, (ctx or {}).get("visible", 125))
    return any(k in vis.lower() for k in kws)


def context_overlap(text, ctx):
    post = (ctx or {}).get("post")
    if not post:
        return None
    mine = {w for w in T.lower_words(text) if len(w) > 3 and w not in STOP}
    theirs = {w for w in T.lower_words(post) if len(w) > 3 and w not in STOP}
    return len(mine & theirs)


def formula_match(text, ctx):
    formulas = (ctx or {}).get("formulas")
    if not formulas:
        return None
    return bool(match_formulas(text, formulas))


def match_formulas(text, formulas):
    out = []
    for f in formulas:
        pat = f.get("match")
        if pat and re.search(pat, text, re.IGNORECASE):
            out.append(f["id"])
    return out


def audience_hit(text, ctx):
    profile = (ctx or {}).get("profile")
    terms = _profile_terms(profile, "audience.search_terms", "audience.identity_terms", "niche.primary")
    if not terms:
        return None
    low = text.lower()
    if any(t.lower() in low for t in terms):
        return True
    words = {w for t in terms for w in T.lower_words(t) if len(w) > 3 and w not in STOP}
    return bool(words & set(T.lower_words(text)))


def banned_hits(text, ctx):
    profile = (ctx or {}).get("profile")
    terms = _profile_terms(profile, "voice.words_i_never_use", "restrictions.never_say")
    if not terms:
        return 0
    return sum(n for _, n in L.find_terms(text, terms))


def closing_ask(text, ctx=None):
    sents = T.sentences(text)
    tail = " ".join(sents[-2:]) if sents else ""
    return bool(L.asks(tail)) or tail.rstrip().endswith("?")


SETUP_RE = re.compile(r"\b(?:in|back in|since) (?:19|20)\d\d\b|\b\w+ (?:years?|months?|weeks?|days?) ago\b|\b(?:years?|months?) later\b", re.IGNORECASE)


def story_arc(text, ctx=None):
    """How many of setup / turn / payoff are signalled (0-3)."""
    lex = L.lexicon()
    setup = bool(L.find_terms(text, lex["story_setup"]) or SETUP_RE.search(text))
    turn = bool(L.find_terms(text, lex["story_turn"]))
    payoff = bool(L.find_terms(text, lex["story_payoff"]))
    return int(setup) + int(turn) + int(payoff)


def _starts_with_filler(text, ctx=None):
    return bool(L.starts_with_any(T.first_line(text), "filler_openers"))


FEATURES = {
    "char_count": lambda t, c: len(t),
    "word_count": lambda t, c: T.word_count(t),
    "sentence_count": lambda t, c: len(T.sentences(t)),
    "line_count": lambda t, c: len(T.lines(t)),
    "first_line_chars": lambda t, c: len(T.first_line(t)),
    "first_line_words": lambda t, c: T.word_count(T.first_line(t)),
    "mean_sentence_words": lambda t, c: (
        sum(T.sentence_lengths(t)) / len(T.sentence_lengths(t)) if T.sentence_lengths(t) else None
    ),
    "has_number": lambda t, c: T.has_number(t),
    "specificity_hits": specificity_hits,
    "specificity_density": lambda t, c: _per100(specificity_hits(t), t),
    "second_person": lambda t, c: bool(L.find_terms(t, L.lexicon()["second_person"])),
    "second_person_density": lambda t, c: _per100(L.count_terms(t, "second_person"), t),
    "first_person": lambda t, c: bool(L.find_terms(t, L.lexicon()["first_person"])),
    "starts_with_greeting": lambda t, c: bool(L.starts_with_any(T.first_line(t), "greetings")),
    "starts_with_filler": _starts_with_filler,
    "starts_with_emoji": lambda t, c: T.starts_with_emoji(T.first_line(t)),
    "starts_with_hashtag": lambda t, c: T.first_line(t).startswith("#"),
    "attention_begging": lambda t, c: L.count_terms(t, "attention_begging"),
    "engagement_bait": lambda t, c: L.count_terms(t, "engagement_bait"),
    "slop_count": lambda t, c: sum(n for _, n in L.slop_hits(t)),
    "slop_density": lambda t, c: _per100(sum(n for _, n in L.slop_hits(t)), t),
    "tell_count": lambda t, c: len(L.tells(t)),
    "hedge_count": lambda t, c: L.count_terms(t, "hedges"),
    "hedge_density": lambda t, c: _per100(L.count_terms(t, "hedges"), t),
    "dash_count": lambda t, c: L.dash_count(t),
    "invisible_count": lambda t, c: len(L.invisible_chars(t)),
    "emoji_count": lambda t, c: T.emoji_count(t),
    "emoji_per_100_chars": lambda t, c: (100.0 * T.emoji_count(t) / len(t)) if t else None,
    "hashtag_count": lambda t, c: len(T.hashtags(t)),
    "generic_hashtag_count": lambda t, c: sum(
        1 for h in T.hashtags(t) if h.lower() in {g.lower() for g in L.lexicon()["generic_hashtags"]}
    ),
    "link_count": lambda t, c: len(T.links(t)),
    "mention_count": lambda t, c: len(T.mentions(t)),
    "ask_count": lambda t, c: len(L.asks(t)),
    "has_ask": lambda t, c: bool(L.asks(t)),
    "closing_ask": closing_ask,
    "question_count": lambda t, c: sum(1 for s in T.sentences(t) if s.rstrip().endswith("?")),
    "tension": lambda t, c: L.count_terms(t, "tension_markers"),
    "curiosity": lambda t, c: L.count_terms(t, "curiosity_markers"),
    "stakes": lambda t, c: L.count_terms(t, "tension_markers") + L.count_terms(t, "curiosity_markers"),
    "keyword_coverage": keyword_coverage,
    "keyword_in_visible": keyword_in_visible,
    "burstiness": lambda t, c: T.burstiness(t),
    "mattr": lambda t, c: T.mattr(t),
    "repeated_trigram_ratio": lambda t, c: T.repeated_ngram_ratio(t, 3),
    "repeated_opener_share": lambda t, c: T.repeated_opener_share(t),
    "triad_count": lambda t, c: len(TRIAD_RE.findall(t)),
    "story_arc": story_arc,
    "value_markers": lambda t, c: L.count_terms(t, "value_markers") + len(NUMBERED_LINE_RE.findall(t)),
    "numbered_lines": lambda t, c: len(NUMBERED_LINE_RE.findall(t)),
    "ref_overlap": lambda t, c: T.shingle_overlap(t, (c or {}).get("refs")),
    "context_overlap": context_overlap,
    "self_promo": lambda t, c: L.count_terms(t, "self_promo"),
    "spam_count": lambda t, c: L.count_terms(t, "spam_markers"),
    "pushy_count": lambda t, c: L.count_terms(t, "pushy_dm"),
    "generic_comment": lambda t, c: L.is_generic_comment(t),
    "unverified_claims": lambda t, c: len(C.unverified_claims(t, (c or {}).get("profile"))),
    "placeholder_count": lambda t, c: len(T.placeholders(t)),
    "formula_match": formula_match,
    "audience_hit": audience_hit,
    "banned_hits": banned_hits,
}


def compute(name, text, ctx=None):
    if name not in FEATURES:
        raise KeyError("unknown feature '%s'. Known: %s" % (name, ", ".join(sorted(FEATURES))))
    return FEATURES[name](text, ctx or {})
