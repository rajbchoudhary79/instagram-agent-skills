#!/usr/bin/env python3
"""Score an Instagram profile snapshot out of 100 and list fixes in priority order.

  profile_audit.py snapshot.json
  profile_audit.py snapshot.json --manual '{"photo": 7, "positioning": 3}'
  profile_audit.py snapshot.json --json

Snapshot (JSON), copied by the creator from their own profile (never fetched):
  {
    "username": "priyabakes",
    "name_field": "Priya Nair | Weeknight Sourdough",
    "bio": "...",
    "links": ["https://..."],
    "profile_photo": "close-up face, off-white background",
    "highlights": [{"title": "Start here"}, ...],
    "pinned": [{"format": "reel", "topic": "..."}, ...],
    "recent_posts": [{"format": "reel", "topic": "...", "pillar": "Starter care"}, ...]
  }

Rubric: profile_rubric.json (10 criteria, 100 points). Manual criteria (photo,
positioning) need a human or agent judgement passed with --manual; until then
the report shows the auto-scored points and what is pending.
"""

import argparse
import json
import os
import re
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, lexicon as L, paths, profile as P, report as R, text as T

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _terms(profile):
    terms = list(P.get(profile or {}, "audience.search_terms") or [])
    if P.get(profile or {}, "niche.primary"):
        terms.append(P.get(profile, "niche.primary"))
    return terms


def audit(snap, profile, manual=None):
    rub = paths.load_json(os.path.join(HERE, "profile_rubric.json"))
    plat = paths.load_config("platform")["profile"]
    manual = manual or {}
    out = {}

    def put(cid, got, notes, fixes=None):
        out[cid] = {"got": round(got, 1), "notes": notes, "fixes": fixes or []}

    pts = {c["id"]: c["points"] for c in rub["criteria"]}

    u = (snap.get("username") or "").lstrip("@")
    s, notes, fixes = pts["username"], [], []
    if not u:
        s, notes = 0, ["no username in snapshot"]
    else:
        if len(u) > plat["username_max_chars"]["value"]:
            s -= 8
            fixes.append("Username over %d characters." % plat["username_max_chars"]["value"])
        if re.search(r"\d{2,}", u):
            s -= 3
            fixes.append("Digits make it hard to say out loud; drop them if you can.")
        if len(re.findall(r"[._]", u)) > 1:
            s -= 3
            fixes.append("More than one separator (. or _).")
        if len(u) > 20:
            s -= 2
            fixes.append("Over 20 characters; shorter is easier to remember.")
        notes.append("@%s (%d chars)" % (u, len(u)))
    put("username", max(0, s), notes, fixes)

    nf = snap.get("name_field") or ""
    terms = _terms(profile)
    s, notes, fixes = 0, [], []
    if len(nf) > plat["name_max_chars"]["value"]:
        fixes.append("Name field over %d characters." % plat["name_max_chars"]["value"])
    elif nf:
        s += 4
    term_hit = [t for t in terms if t.lower() in nf.lower()] or (
        [w for t in terms for w in T.lower_words(t) if len(w) > 4 and w in T.lower_words(nf)])
    if term_hit:
        s += 8
        notes.append("contains search term: %s" % term_hit[0])
    else:
        fixes.append("Add the phrase people search for to the name field (e.g. '%s'). It is searchable; the bio is not."
                     % (terms[0] if terms else "your niche"))
    if nf and u and nf.replace(" ", "").lower() == u.replace("_", "").replace(".", "").lower():
        s = max(0, s - 4)
        fixes.append("Name field repeats the username; use it for the search phrase.")
    put("name_field", min(pts["name_field"], s), notes, fixes)

    bio = snap.get("bio") or ""
    ctx = {"profile": profile, "keywords": P.get(profile or {}, "audience.search_terms") or None}
    bres = engine.score(bio, "bio", ctx) if bio else None
    if bres:
        bfix = [r.get("fix") for c in bres["criteria"] for r in c["rules"] if r.get("fix")]
        bfix += [d["message"] for d in bres["dealbreakers"]]
        put("bio", pts["bio"] * bres["score"] / 100.0, ["bio rubric %.0f (%s), %d/%d chars" % (bres["score"], bres["band"], len(bio), plat["bio_max_chars"]["value"])], bfix)
    else:
        put("bio", 0, ["no bio"], ["Write a bio: who it's for, what they get, one proof point, one next step."])

    asks = L.asks(bio)
    pointer = re.search(r"[↓⬇👇]|\bbelow\b|\bDM\b|\bfree\b|\bget\b|\bgrab\b", bio, re.IGNORECASE)
    if asks:
        put("bio_cta", pts["bio_cta"], ["ask: %s" % ", ".join(asks)])
    elif pointer:
        put("bio_cta", pts["bio_cta"] * 0.6, ["points at the link but no explicit action"], ["Make the action explicit: 'Get the free template ↓'."])
    else:
        put("bio_cta", 0, [], ["End the bio with one action: what to tap, or which word to DM."])

    links = snap.get("links") or []
    if not links:
        put("link", 0, [], ["Add a link. One destination that matches the bio's call to action."])
    elif len(links) > plat["bio_links_max"]["value"]:
        put("link", 4, ["%d links" % len(links)], ["More links than Instagram allows (%d)." % plat["bio_links_max"]["value"]])
    else:
        put("link", pts["link"] if (asks or pointer) else 5, ["%d link(s)" % len(links)],
            [] if (asks or pointer) else ["The bio does not say what is behind the link."])

    hl = snap.get("highlights") or []
    s, notes, fixes = 0, ["%d highlights" % len(hl)], []
    if 3 <= len(hl) <= 7:
        s += 6
    elif hl:
        s += 3
        fixes.append("Aim for 3-7 highlights (you have %d). Too few leaves visitors nothing to tap; too many and none get tapped." % len(hl))
    else:
        fixes.append("Add highlights: Start here, an offer or freebie, and proof (results, reviews or work).")
    mx = plat["highlight_title_visible_chars"]["value"]
    long_titles = [h.get("title", "") for h in hl if len(h.get("title", "")) > mx]
    if hl and not long_titles:
        s += 2
    elif long_titles:
        fixes.append("Titles over ~%d characters get cut: %s" % (mx, ", ".join(long_titles)))
    if any(any(k in (h.get("title") or "").lower() for k in rub["highlight_keywords"]) for h in hl):
        s += 2
    elif hl:
        fixes.append("No start-here, offer or proof highlight.")
    put("highlights", s, notes, fixes)

    pin = snap.get("pinned") or []
    put("pinned", {0: 0, 1: 3, 2: 5}.get(len(pin), pts["pinned"]), ["%d pinned" % len(pin)],
        [] if len(pin) >= 3 else ["Pin three posts: who you are, your best value post, proof or the offer."])

    posts = snap.get("recent_posts") or []
    pillars = [p.get("name", "") for p in (P.get(profile or {}, "niche.pillars") or []) if isinstance(p, dict)]
    if len(posts) < 6 or not pillars:
        reason = "need 6+ recent posts" if len(posts) < 6 else "no pillars in the creator profile"
        put("consistency", 0, ["not scored: %s" % reason], ["List the last 9-12 posts with their pillar to score this."])
        out["consistency"]["pending"] = True
    else:
        pl = [x.lower() for x in pillars]
        inside = sum(1 for p in posts if (p.get("pillar") or "").lower() in pl or
                     any(x in (p.get("topic") or "").lower() for x in pl))
        share = inside / len(posts)
        put("consistency", pts["consistency"] * min(1.0, share / 0.8), ["%d of %d posts inside pillars" % (inside, len(posts))],
            [] if share >= 0.8 else ["%d%% of recent posts are off-pillar. New visitors cannot tell what the account is about." % round(100 * (1 - share))])

    for c in rub["criteria"]:
        if c["mode"] == "manual":
            if c["id"] in manual:
                v = max(0, min(c["points"], float(manual[c["id"]])))
                put(c["id"], v, ["manual score"], [] if v >= c["points"] * 0.8 else [c["full_marks"]])
            else:
                put(c["id"], 0, ["pending manual review"], [c["full_marks"]])
                out[c["id"]]["pending"] = True

    pending = [cid for cid, v in out.items() if v.get("pending")]
    scored_points = sum(pts[c] for c in pts if c not in pending)
    got = sum(v["got"] for cid, v in out.items() if cid not in pending)
    rows = []
    for c in rub["criteria"]:
        v = out[c["id"]]
        rows.append({"id": c["id"], "label": c["label"], "points": c["points"], "got": v["got"],
                     "lost": round(c["points"] - v["got"], 1), "pending": bool(v.get("pending")),
                     "notes": v["notes"], "fixes": v["fixes"], "full_marks": c["full_marks"]})
    order = sorted([r for r in rows if r["fixes"] and not r["pending"]], key=lambda r: r["lost"], reverse=True)
    return {"total": round(got, 1), "out_of": scored_points, "pending": pending,
            "normalised": round(100.0 * got / scored_points, 1) if scored_points else None,
            "criteria": rows, "fix_order": [r["id"] for r in order]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snapshot")
    ap.add_argument("--manual", help='JSON of manual scores, e.g. \'{"photo": 8, "positioning": 3}\', or a file')
    cli.add_common(ap, keywords=False)
    args = ap.parse_args(argv)
    ctx, prof = cli.build_ctx(args, use_profile_keywords=False)
    snap = json.loads(paths.read_text(args.snapshot))
    manual = None
    if args.manual:
        manual = json.loads(paths.read_text(args.manual) if os.path.isfile(args.manual) else args.manual)
    res = audit(snap, ctx.get("profile"), manual)
    if args.json:
        R.emit_json(res)
        return 0
    print("PROFILE AUDIT  @%s" % (snap.get("username") or "?").lstrip("@"))
    print("=" * 78)
    for r in res["criteria"]:
        got = "pending" if r["pending"] else "%4.1f" % r["got"]
        print("  %-20s %7s / %-3d %s" % (r["label"], got, r["points"], "; ".join(r["notes"])))
    print("-" * 78)
    if res["pending"]:
        print("  SCORE %.1f of %d auto-scored points (%.0f%%). Pending: %s (%d points)."
              % (res["total"], res["out_of"], res["normalised"] or 0, ", ".join(res["pending"]), 100 - res["out_of"]))
    else:
        print("  SCORE %.1f / 100" % res["total"])
    print("\nFIX FIRST (most points lost first)")
    n = 0
    for cid in res["fix_order"]:
        r = next(x for x in res["criteria"] if x["id"] == cid)
        for f in r["fixes"]:
            n += 1
            print("  %2d. [%s, -%.1f] %s" % (n, r["label"], r["lost"], f))
    for cid in res["pending"]:
        r = next(x for x in res["criteria"] if x["id"] == cid)
        print("  --  [%s] needs review: %s" % (r["label"], r["full_marks"]))
    if prof is None:
        print("\n(no creator profile: search-term and pillar checks are weaker)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
