"""Term-list matching over config/lexicon.json."""

import re

from . import paths, text as T

_CACHE = {}


def lexicon():
    if "lex" not in _CACHE:
        _CACHE["lex"] = paths.load_config("lexicon")
    return _CACHE["lex"]


def _term_re(term):
    key = ("re", term)
    if key not in _CACHE:
        _CACHE[key] = re.compile(r"(?<![\w'’])" + re.escape(term.lower()) + r"(?![\w'’])")
    return _CACHE[key]


def _norm(s):
    return s.replace("’", "'").lower()


def find_terms(text, terms):
    """Return [(term, count)] for every term in terms found in text."""
    low = _norm(text)
    hits = []
    for term in terms:
        n = len(_term_re(term).findall(low))
        if n:
            hits.append((term, n))
    return hits


def count_terms(text, list_name):
    return sum(n for _, n in find_terms(text, lexicon()[list_name]))


def starts_with_any(text, list_name):
    """True when the first words of text match an entry in the named list."""
    low = _norm(T.strip_emoji(text)).strip().lstrip("\"'“‘([").strip()
    for term in lexicon()[list_name]:
        if low == term or re.match(re.escape(term) + r"(?![\w'])", low):
            return term
    return None


def slop_hits(text):
    lex = lexicon()
    return find_terms(text, lex["slop_phrases"]) + find_terms(text, lex["slop_words"])


def tells(text):
    out = []
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    for tell in lexicon()["tells"]:
        for m in re.finditer(tell["pattern"], text, re.IGNORECASE | re.MULTILINE):
            out.append({"id": tell["id"], "match": m.group(0), "message": tell["message"]})
    return out


def invisible_chars(text):
    """[(index, codepoint_hex, name)] for invisible / format characters.

    ZWJ and VS16 are allowed inside emoji sequences, where they are legitimate.
    """
    table = lexicon()["invisible_chars"]
    found = []
    for i, ch in enumerate(text):
        cp = ord(ch)
        code = "%04X" % cp
        if 0xE0000 <= cp <= 0xE007F:
            found.append((i, code, "tag character"))
            continue
        if code not in table:
            continue
        if code in ("200D", "FE0F"):
            prev_e = i > 0 and T.is_emoji_char(text[i - 1])
            next_e = i + 1 < len(text) and T.is_emoji_char(text[i + 1])
            if code == "FE0F" and i > 0 and (prev_e or text[i - 1] in "0123456789#*❤☺☹"):
                continue
            if code == "200D" and next_e and (prev_e or (i > 0 and ord(text[i - 1]) == 0xFE0F)):
                continue
        found.append((i, code, table[code]))
    return found


def dash_count(text):
    return sum(text.count(d) for d in lexicon()["dash_chars"])


def is_generic_comment(text):
    """True when a comment is nothing but generic praise and/or emoji."""
    core = _norm(T.strip_emoji(text))
    core = re.sub(r"[^\w\s%']", " ", core)
    core = re.sub(r"\s+", " ", core).strip()
    if not core:
        return True
    generic = sorted((g.lower() for g in lexicon()["generic_comments"]), key=len, reverse=True)
    rest = core
    for g in generic:
        rest = re.sub(r"(?<!\w)" + re.escape(g) + r"(?!\w)", " ", rest)
    rest = re.sub(r"\b(?:so|very|really|such|a|an|the|bro|man|girl|omg|lol|haha|this|is|it|thank|thanks|you|yes|always)\b", " ", rest)
    return not rest.strip()


def asks(text):
    """Distinct call-to-action types found: comment, save, share, follow, dm, link, book."""
    found = []
    for kind, pattern in lexicon()["cta_patterns"].items():
        if kind.startswith("_"):
            continue
        if re.search(pattern, text):
            found.append(kind)
    return found
