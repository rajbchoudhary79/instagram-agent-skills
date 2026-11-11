"""The rubric scoring engine.

A rubric is JSON (config/rubrics/<id>.json). It lists weighted criteria; each
criterion is one or more rules; each rule turns one named feature into a
0-100 score. Dealbreakers cap the total. See docs/scoring.md for the format.

Rule types
  range   {"ideal": [lo, hi], "zero_at": [lo0, hi0]}  100 inside ideal, linear to 0 at the bounds
  max     {"good": g, "zero_at": z}                   lower is better: 100 at <= g, 0 at >= z
  min     {"zero_at": z, "good": g}                   higher is better: 0 at <= z, 100 at >= g
  bool    {"true": s1, "false": s2}                   fixed score per value

A rule whose feature returns None is "not measured": it is skipped and reported,
and the criterion weights are renormalised over what was measured.
"""

import json
import os

from . import features as F
from . import paths

OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a is not None and a >= b,
    "<=": lambda a, b: a is not None and a <= b,
    ">": lambda a, b: a is not None and a > b,
    "<": lambda a, b: a is not None and a < b,
}
RULE_TYPES = ("range", "max", "min", "bool")


def rubric_path(name_or_path):
    if os.path.isfile(name_or_path):
        return name_or_path
    override = os.path.join(paths.data_home(), "rubrics", name_or_path + ".json")
    if os.path.isfile(override):
        return override
    return paths.config_path("rubrics", name_or_path + ".json")


def load_rubric(name_or_path):
    p = rubric_path(name_or_path)
    if not os.path.isfile(p):
        raise FileNotFoundError("no rubric '%s' (looked for %s)" % (name_or_path, p))
    with open(p, "r", encoding="utf-8") as fh:
        rubric = json.load(fh)
    problems = check_rubric(rubric)
    if problems:
        raise ValueError("rubric %s is invalid:\n  " % p + "\n  ".join(problems))
    return rubric


def list_rubrics():
    d = paths.config_path("rubrics")
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def check_rubric(rubric):
    """Structural checks. Returns a list of problems (empty when fine)."""
    probs = []
    for key in ("id", "name", "measures", "limitations", "bands", "criteria"):
        if key not in rubric:
            probs.append("missing '%s'" % key)
    if probs:
        return probs
    if not rubric["criteria"]:
        probs.append("no criteria")
    for c in rubric["criteria"]:
        cid = c.get("id", "?")
        if not isinstance(c.get("weight"), (int, float)) or c["weight"] <= 0:
            probs.append("criterion %s: weight must be > 0" % cid)
        if not c.get("measures"):
            probs.append("criterion %s: missing 'measures'" % cid)
        for r in c.get("rules", []):
            probs.extend("criterion %s: %s" % (cid, p) for p in _check_rule(r))
        if not c.get("rules"):
            probs.append("criterion %s: no rules" % cid)
    for d in rubric.get("dealbreakers", []):
        if d.get("feature") not in F.FEATURES:
            probs.append("dealbreaker %s: unknown feature %s" % (d.get("id"), d.get("feature")))
        if d.get("op") not in OPS:
            probs.append("dealbreaker %s: bad op %s" % (d.get("id"), d.get("op")))
        if not isinstance(d.get("cap"), (int, float)):
            probs.append("dealbreaker %s: cap must be a number" % d.get("id"))
    return probs


def _check_rule(r):
    probs = []
    if r.get("feature") not in F.FEATURES:
        probs.append("unknown feature %r" % r.get("feature"))
    t = r.get("type")
    if t not in RULE_TYPES:
        probs.append("bad rule type %r" % t)
    elif t == "range" and not (len(r.get("ideal", [])) == 2 and len(r.get("zero_at", [])) == 2):
        probs.append("range rule needs ideal and zero_at pairs")
    elif t in ("max", "min") and not ("good" in r and "zero_at" in r):
        probs.append("%s rule needs good and zero_at" % t)
    elif t == "bool" and not ("true" in r and "false" in r):
        probs.append("bool rule needs true and false scores")
    if not r.get("why"):
        probs.append("rule on %s has no 'why'" % r.get("feature"))
    return probs


def _lerp(v, a, b):
    """0 at a, 100 at b, clamped."""
    if a == b:
        return 100.0 if v >= b else 0.0
    return max(0.0, min(100.0, 100.0 * (v - a) / (b - a)))


def score_rule(rule, value):
    t = rule["type"]
    if value is None:
        return None
    if t == "bool":
        return float(rule["true"] if value else rule["false"])
    v = float(value)
    if t == "range":
        lo, hi = rule["ideal"]
        lo0, hi0 = rule["zero_at"]
        if lo <= v <= hi:
            return 100.0
        if v < lo:
            return _lerp(v, lo0, lo)
        return _lerp(v, hi0, hi)
    if t == "max":
        return 100.0 - _lerp(v, rule["good"], rule["zero_at"]) if v > rule["good"] else 100.0
    if t == "min":
        return _lerp(v, rule["zero_at"], rule["good"])
    raise ValueError(t)


def _band(total, bands):
    if total >= bands.get("strong", 80):
        return "STRONG"
    if total >= bands.get("ok", 55):
        return "OK"
    return "WEAK"


def score(text, rubric, ctx=None):
    """Score text against a rubric dict (or rubric name). Returns a JSON-able result."""
    if isinstance(rubric, str):
        rubric = load_rubric(rubric)
    ctx = ctx or {}
    cache = {}

    def feat(name):
        if name not in cache:
            cache[name] = F.compute(name, text, ctx)
        return cache[name]

    crit_out = []
    num = den = total_w = 0.0
    for c in rubric["criteria"]:
        total_w += c["weight"]
        rules_out = []
        rn = rd = 0.0
        for r in c["rules"]:
            val = feat(r["feature"])
            s = score_rule(r, val)
            w = r.get("weight", 1.0)
            entry = {"feature": r["feature"], "value": _round(val), "score": _round(s), "why": r["why"]}
            if s is not None and s < 70 and r.get("fix"):
                entry["fix"] = r["fix"]
            if s is None:
                entry["note"] = r.get("unmeasured", "not measurable for this input")
            rules_out.append(entry)
            if s is not None:
                rn += s * w
                rd += w
        cscore = rn / rd if rd else None
        crit_out.append({
            "id": c["id"], "label": c.get("label", c["id"]), "weight": c["weight"],
            "measures": c["measures"], "score": _round(cscore), "rules": rules_out,
        })
        if cscore is not None:
            num += cscore * c["weight"]
            den += c["weight"]

    raw = num / den if den else 0.0
    triggered = []
    total = raw
    for d in rubric.get("dealbreakers", []):
        val = feat(d["feature"])
        if val is not None and OPS[d["op"]](val, d["value"]):
            triggered.append({"id": d["id"], "cap": d["cap"], "message": d["message"], "value": _round(val)})
            total = min(total, float(d["cap"]))

    measured = [c for c in crit_out if c["score"] is not None]
    weakest = min(measured, key=lambda c: c["score"]) if measured else None
    return {
        "rubric": rubric["id"],
        "name": rubric["name"],
        "score": round(total, 1),
        "raw_score": round(raw, 1),
        "band": _band(total, rubric["bands"]) if den else "UNMEASURED",
        "measured_share": round(den / total_w, 2) if total_w else 0.0,
        "criteria": crit_out,
        "dealbreakers": triggered,
        "weakest": weakest["id"] if weakest else None,
        "measures": rubric["measures"],
        "limitations": rubric["limitations"],
    }


def _round(v):
    if isinstance(v, float):
        return round(v, 2)
    return v


def render(result, show_limits=True, width=78):
    """Plain-text explanation of a score: what was measured, why it landed there."""
    from . import report as R
    lines = []
    lines.append("%s  %5.1f  %s" % (result["name"].upper(), result["score"], result["band"]))
    if result["raw_score"] != result["score"]:
        lines.append("  (capped from %.1f by a dealbreaker)" % result["raw_score"])
    lines.append("-" * width)
    for c in result["criteria"]:
        if c["score"] is None:
            lines.append("  %-22s   --  not measured: %s" % (c["label"], c["rules"][0].get("note", "")))
            continue
        lines.append("  %-22s %5.0f  %s" % (c["label"], c["score"], R.bar(c["score"])))
        for r in c["rules"]:
            if r["score"] is None:
                continue
            mark = "  " if r["score"] >= 70 else "! "
            lines.append("      %s%s = %s -> %.0f. %s" % (mark, r["feature"], _fmt(r["value"]), r["score"], r["why"]))
            if r.get("fix"):
                lines.append("        fix: %s" % r["fix"])
    for d in result["dealbreakers"]:
        lines.append("  DEALBREAKER (cap %s): %s" % (d["cap"], d["message"]))
    if result["measured_share"] < 1.0:
        lines.append("  Partial score: %.0f%% of the rubric weight was measurable for this input."
                     % (100 * result["measured_share"]))
    if show_limits:
        lines.append("  Measures: " + result["measures"])
        for lim in result["limitations"]:
            lines.append("  Limit: " + lim)
    return "\n".join(lines)


def _fmt(v):
    if isinstance(v, float):
        return "%.2f" % v
    return str(v)
