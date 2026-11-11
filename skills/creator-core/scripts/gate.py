#!/usr/bin/env python3
"""Final quality gate. Run it on anything before it goes to the user for approval.

  gate.py draft.txt --type caption
  gate.py script.txt --type reel
  gate.py reply.txt --type comment --post their_post.txt
  gate.py draft.txt --type dm --json

Types: caption reel carousel story comment reply dm bio generic (config/gate.json)

Verdicts
  BLOCKED  a hard failure: invisible characters, a banned word, an unverified
           claim, or a platform limit. Fix before showing it as final.
  REVIEW   warnings: placeholders to fill, a rubric under its threshold.
           Show the user, and say what the warnings are.
  READY    nothing found. Still the user's call: the gate never posts anything.

Exit codes: 0 READY, 1 REVIEW, 2 BLOCKED.
"""

import argparse
import re
import sys

import _bootstrap  # noqa: F401
from igkit import claims as C
from igkit import cli, engine, lexicon as L, paths, profile as P, report as R, text as T

ANNOTATION_RE = re.compile(r"\[[^\]]*\]|^\s*#.*$|^\s*[A-Z][A-Z /-]{1,20}:\s*", re.MULTILINE)


def spoken(text):
    """Strip script annotations ([visual: ...], # notes, LABEL:) to the words that ship."""
    return "\n".join(ln for ln in ANNOTATION_RE.sub("", text).splitlines() if ln.strip())


def run_gate(raw, ctype, ctx):
    cfg = paths.load_config("gate")["types"][ctype]
    plat = paths.load_config("platform")
    profile = ctx.get("profile")
    text = spoken(raw) if ctype in ("reel", "carousel", "story") else raw
    checks = []

    inv = L.invisible_chars(raw)
    if inv:
        kinds = sorted({name for _, _, name in inv})
        checks.append({"level": "FAIL", "id": "invisible",
                       "message": "%d invisible character(s): %s. Run content-humanizer rewrite_check.py clean." % (len(inv), ", ".join(kinds))})

    banned_terms = (P.get(profile or {}, "voice.words_i_never_use") or []) + (P.get(profile or {}, "restrictions.never_say") or [])
    for term, n in L.find_terms(text, banned_terms):
        checks.append({"level": "FAIL", "id": "banned", "message": "Uses '%s' (%dx), which the creator never says." % (term, n)})

    for term, n in L.find_terms(text, P.get(profile or {}, "restrictions.topics_off_limits") or []):
        checks.append({"level": "WARN", "id": "off_limits", "message": "Touches an off-limits topic: '%s'." % term})

    for c in C.unverified_claims(text, profile):
        level = "WARN" if c["type"] == "credential" else "FAIL"
        checks.append({"level": level, "id": "claim",
                       "message": "Unverified %s '%s'. Add it to verified_facts if true, else use a {{placeholder}}." % (c["type"], c["match"])})

    ph = T.placeholders(text)
    if ph:
        checks.append({"level": "WARN", "id": "placeholders",
                       "message": "%d placeholder(s) to fill before posting: %s" % (len(ph), ", ".join(sorted(set(ph))))})

    limits = cfg.get("limits")
    if limits == "caption":
        cap = plat["caption"]
        if len(text) > cap["max_chars"]["value"]:
            checks.append({"level": "FAIL", "id": "length", "message": "%d characters; the limit is %d." % (len(text), cap["max_chars"]["value"])})
        nt = len(T.hashtags(text))
        if nt > cap["max_hashtags"]["value"]:
            checks.append({"level": "FAIL", "id": "hashtags",
                           "message": "%d hashtags; configured cap is %d (%s confidence)." % (nt, cap["max_hashtags"]["value"], cap["max_hashtags"]["confidence"])})
    elif limits == "bio":
        mx = plat["profile"]["bio_max_chars"]["value"]
        if len(text) > mx:
            checks.append({"level": "FAIL", "id": "length", "message": "Bio is %d characters; the limit is %d." % (len(text), mx)})

    scores = {}
    for name, threshold in cfg.get("rubrics", {}).items():
        res = engine.score(text, name, ctx)
        scores[name] = res
        lvl = "PASS" if res["score"] >= threshold else "WARN"
        msg = "%s %.0f (threshold %d)%s" % (res["name"], res["score"], threshold,
                                            "" if lvl == "PASS" else "; weakest: %s" % res["weakest"])
        checks.append({"level": lvl, "id": "rubric:" + name, "message": msg})
    for name, threshold in cfg.get("first_line", {}).items():
        fl = T.first_line(text)
        if not fl:
            continue
        hctx = dict(ctx, formulas=paths.load_config("hook_formulas")["formulas"])
        res = engine.score(fl, name, hctx)
        scores["first_line:" + name] = res
        lvl = "PASS" if res["score"] >= threshold else "WARN"
        checks.append({"level": lvl, "id": "first_line:" + name,
                       "message": "First line as a hook: %.0f (threshold %d)" % (res["score"], threshold)})

    disclaimers = P.get(profile or {}, "restrictions.disclaimers") or []
    if disclaimers and ctype in ("caption", "reel", "carousel", "story"):
        missing = [d for d in disclaimers if d.lower() not in raw.lower()]
        if missing:
            checks.append({"level": "WARN", "id": "disclaimer", "message": "Required disclaimer not found: " + "; ".join(missing)})

    if profile is None:
        checks.append({"level": "INFO", "id": "profile", "message": "No creator profile loaded: banned words and verified facts not checked."})

    return {"type": ctype, "verdict": R.verdict(checks), "checks": checks,
            "scores": {k: {"score": v["score"], "band": v["band"], "weakest": v["weakest"]} for k, v in scores.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="draft file, or - for stdin")
    ap.add_argument("--type", default="generic", choices=sorted(paths.load_config("gate")["types"]))
    cli.add_common(ap, post=True)
    args = ap.parse_args(argv)
    ctx, prof = cli.build_ctx(args)
    result = run_gate(paths.read_text(args.file), args.type, ctx)
    result["profile"] = prof
    if args.json:
        R.emit_json(result)
    else:
        print("QUALITY GATE  type=%s  profile=%s" % (args.type, prof or "none"))
        print("=" * 78)
        print(R.render_checks(result["checks"]))
        print("-" * 78)
        print("VERDICT: %s" % result["verdict"])
        print("Nothing has been posted or sent. Publishing is the creator's decision.")
    return {"READY": 0, "REVIEW": 1, "BLOCKED": 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
