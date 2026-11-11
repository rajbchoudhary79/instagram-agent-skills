"""Find factual claims in a draft and check them against the creator's verified facts.

The point is the no-fabrication rule: any metric, result, credential or
achievement that ships under the creator's name must trace back to an entry in
profile.verified_facts, or stay a {{placeholder}} until the creator fills it.

Detection is deliberately over-eager. A false alarm costs a glance; a missed
invented number costs the creator's credibility.
"""

import re

from . import text as T

METRIC_RE = re.compile(
    r"[$€£₹]\s?\d[\d,.]*\d(?:\s?(?:k|K|m|M|bn|million|thousand)\b)?|[$€£₹]\s?\d(?:\s?(?:k|K|m|M|bn|million|thousand)\b)?"
    r"|\d[\d,.]*\s?(?:%|percent|x\b|X\b|k\b|K\b|M\b)"
    r"|\d[\d,.]*\+?\s+(?:followers|subscribers|clients|customers|students|members|sales|views|downloads|"
    r"leads|signups|sign-ups|users|people|years of|reviews|five-star|5-star|countries|brands|businesses)",
)
ACHIEVEMENT_RE = re.compile(
    r"\b(?:i|we|my (?:team|business|clients?|students?|company))\s+(?:have\s+|'ve\s+|’ve\s+)?"
    r"(?:made|earned|grew|built|sold|helped|scaled|generated|landed|won|booked|closed|doubled|tripled|"
    r"hit|reached|raised|saved|coached|trained|taught|worked with|served|launched)\b",
    re.IGNORECASE,
)
AUTHORITY_RE = re.compile(
    r"\b(?:award[- ]winning|featured (?:in|on)|as seen (?:in|on)|best[- ]selling|#1|number one|"
    r"certified|board[- ]certified|licensed|top \d+%?|ranked)\b",
    re.IGNORECASE,
)
TESTIMONIAL_RE = re.compile(r"[\"“][^\"”]{8,}[\"”]\s*[-–—]\s*[A-Z][a-z]+")


def _digits(s):
    return re.sub(r"[^\d]", "", s)


def find_claims(text):
    """Return [{'type', 'match', 'sentence'}] for every claim-like span outside {{placeholders}}."""
    clean = T.PLACEHOLDER_RE.sub(" ", text)
    out = []
    for sent in T.sentences(clean):
        for m in METRIC_RE.finditer(sent):
            out.append({"type": "metric", "match": m.group(0).strip(), "sentence": sent})
        for m in ACHIEVEMENT_RE.finditer(sent):
            out.append({"type": "achievement", "match": m.group(0).strip(), "sentence": sent})
        for m in AUTHORITY_RE.finditer(sent):
            out.append({"type": "credential", "match": m.group(0).strip(), "sentence": sent})
        for m in TESTIMONIAL_RE.finditer(sent):
            out.append({"type": "testimonial", "match": m.group(0).strip(), "sentence": sent})
    return out


def _fact_texts(profile):
    facts = (profile or {}).get("verified_facts") or []
    texts = []
    for f in facts:
        if isinstance(f, dict):
            texts.append(str(f.get("claim", "")))
        else:
            texts.append(str(f))
    return [t for t in texts if t.strip()]


def is_verified(claim, profile):
    facts = _fact_texts(profile)
    if not facts:
        return False
    nums = [_digits(n) for n in T.numbers(claim["match"]) if _digits(n)]
    if nums:
        return any(all(n in _fact_numbers(f) for n in nums) for f in facts)
    sent_nums = [_digits(n) for n in T.numbers(claim["sentence"]) if _digits(n)]
    if sent_nums and any(all(n in _fact_numbers(f) for n in sent_nums) for f in facts):
        return True
    sent_words = set(T.lower_words(claim["sentence"])) - _STOP
    for f in facts:
        fw = set(T.lower_words(f)) - _STOP
        if fw and len(sent_words & fw) / len(fw) >= 0.6:
            return True
    return False


def _fact_numbers(s):
    return {_digits(n) for n in T.numbers(s) if _digits(n)}


_STOP = {"i", "we", "my", "the", "a", "an", "and", "of", "to", "in", "for", "with", "have", "has", "our", "on", "at", "is"}


def unverified_claims(text, profile):
    return [c for c in find_claims(text) if not is_verified(c, profile)]
