"""The shared creator profile.

Lookup order for profile.json:
  1. an explicit path (--profile)
  2. $IG_PROFILE
  3. ./.creator-content-kit/profile.json in the current project (searching upwards)
  4. $IG_AGENT_HOME/profile.json, default ~/.creator-content-kit/profile.json

Long-form companions (voice.md, brand.md, audience.md, content-strategy.md)
are read from the same folder when present.
"""

import json
import os

from . import paths, schema

COMPANIONS = ("voice.md", "brand.md", "audience.md", "content-strategy.md")

# (dotted path, weight, why it matters) - drives the completeness score.
IMPORTANT_FIELDS = [
    ("identity.name", 5, "byline and sign-offs"),
    ("identity.handle", 3, "profile audit and @mentions"),
    ("identity.one_liner", 6, "bio and positioning"),
    ("identity.offer", 5, "CTAs, DMs, conversion stories"),
    ("niche.primary", 8, "every skill"),
    ("niche.pillars", 6, "planner balance, audit grouping"),
    ("audience.who", 8, "every skill"),
    ("audience.pains", 6, "hooks and comments"),
    ("audience.search_terms", 5, "captions and bio keywords"),
    ("positioning.statement", 5, "profile audit, carousels"),
    ("language.primary", 4, "every skill"),
    ("voice.tone", 6, "every skill"),
    ("voice.words_i_never_use", 4, "humanizer and final gate"),
    ("voice.sample_texts", 8, "voice matching; the single best input"),
    ("content.formats_preferred", 3, "planner"),
    ("content.posts_per_week", 3, "planner"),
    ("visual.style", 3, "carousel and reel visual direction"),
    ("restrictions.never_say", 2, "final gate"),
    ("goals.primary", 5, "CTA choice, audit"),
    ("goals.cta.keyword", 3, "keyword DM funnels"),
    ("verified_facts", 1, "lets the gate accept real numbers instead of flagging them"),
]


def resolve_path(explicit=None):
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    env = os.environ.get("IG_PROFILE")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    if not os.environ.get("IG_AGENT_HOME"):
        local = paths.find_local_dir()
        if local and os.path.isfile(os.path.join(local, "profile.json")):
            return os.path.join(local, "profile.json")
    return os.path.join(paths.data_home(), "profile.json")


def load(explicit=None):
    """Return (profile_dict or None, path, errors)."""
    p = resolve_path(explicit)
    if not os.path.isfile(p):
        return None, p, ["no profile at %s" % p]
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as exc:
        return None, p, ["profile is not valid JSON: %s" % exc]
    errs = schema.validate(data, paths.load_json(paths.config_path("profile.schema.json")))
    return data, p, errs


def companions(profile_path):
    folder = os.path.dirname(profile_path)
    return [os.path.join(folder, c) for c in COMPANIONS if os.path.isfile(os.path.join(folder, c))]


def get(profile, dotted, default=None):
    node = profile
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def _filled(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return any(_filled(x) for x in (v.values() if isinstance(v, dict) else v))
    return True


def completeness(profile):
    """Return (percent, [missing (field, why)])."""
    total = sum(w for _, w, _ in IMPORTANT_FIELDS)
    got = 0
    missing = []
    for field, w, why in IMPORTANT_FIELDS:
        if _filled(get(profile or {}, field)):
            got += w
        else:
            missing.append((field, why))
    return round(100.0 * got / total), missing


def template_path():
    return os.path.join(paths.CORE_DIR, "templates", "profile.json")


def brief(profile, path):
    """A compact text summary for an agent to read before writing anything."""
    g = lambda k, d="": get(profile, k, d)  # noqa: E731
    join = lambda v: ", ".join(v) if isinstance(v, list) else (v or "")  # noqa: E731
    pillars = g("niche.pillars", []) or []
    pill = ", ".join("%s%s" % (p.get("name"), " (%d%%)" % round(100 * p["share"]) if p.get("share") else "")
                     for p in pillars if isinstance(p, dict))
    pct, missing = completeness(profile)
    rows = [
        ("Creator", "%s %s" % (g("identity.name"), ("@" + g("identity.handle").lstrip("@")) if g("identity.handle") else "")),
        ("One-liner", g("identity.one_liner")),
        ("Offer", g("identity.offer")),
        ("Niche", g("niche.primary") + (" / " + join(g("niche.sub_niches")) if g("niche.sub_niches") else "")),
        ("Pillars", pill),
        ("Audience", g("audience.who")),
        ("Pains", join(g("audience.pains"))),
        ("Search terms", join(g("audience.search_terms"))),
        ("Positioning", g("positioning.statement")),
        ("Language", g("language.primary") + (" (%s)" % g("language.variant") if g("language.variant") else "")),
        ("Tone", join(g("voice.tone"))),
        ("Personality", join(g("voice.personality"))),
        ("On camera", g("voice.on_camera")),
        ("Uses", join(g("voice.words_i_use"))),
        ("Never uses", join(g("voice.words_i_never_use"))),
        ("Emoji", g("voice.emoji_policy")),
        ("Formats", join(g("content.formats_preferred"))),
        ("Visual", g("visual.style")),
        ("Off limits", join((g("restrictions.never_say") or []) + (g("restrictions.topics_off_limits") or []))),
        ("Disclaimers", join(g("restrictions.disclaimers"))),
        ("Goal", g("goals.primary")),
        ("CTA keyword", g("goals.cta.keyword")),
        ("Verified facts", "%d on file" % len(g("verified_facts", []) or [])),
        ("Voice samples", "%d on file" % len(g("voice.sample_texts", []) or [])),
    ]
    out = ["CREATOR PROFILE  (%s)  %d%% complete" % (path, pct)]
    out += ["  %-15s %s" % (k, v) for k, v in rows if v and str(v).strip()]
    comp = companions(path)
    if comp:
        out.append("  Companion docs: " + ", ".join(comp))
    if missing:
        out.append("  Missing: " + ", ".join(f for f, _ in missing[:8]) + (" ..." if len(missing) > 8 else ""))
    out.append("  Rule: never invent experiences, numbers, clients or results. Use {{placeholders}}.")
    return "\n".join(out)
