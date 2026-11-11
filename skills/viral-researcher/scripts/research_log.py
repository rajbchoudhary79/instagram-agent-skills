#!/usr/bin/env python3
"""Rank observed posts against their own account's baseline and build a research log.

  research_log.py observations.csv                          ranking + pattern summary
  research_log.py observations.csv --md research.md            write the research log
  research_log.py observations.csv --save                   add to the reusable library
  research_log.py --library                                 show the saved library
  research_log.py observations.json --json

Input: CSV or JSON (list of objects). Columns, case-insensitive, any order:
  url, account, format, hook, topic, views, likes, comments, shares, saves,
  posted, account_median_views, followers, source, notes
Numbers may be written 12.3K / 1.2M / 4,512. Blank means unknown.

Honesty rules built in:
  - Nothing missing is estimated. Blank stays blank and is reported as such.
  - A post's multiple is its views divided by the median views of the same
    account, so big and small accounts compare fairly. That median is
    'provided' (you gave account_median_views) or 'derived' (median of 5+ posts
    from that account in this file). Otherwise the post is listed as unranked.
  - Every number is labelled as user-supplied, not independently verified.
"""

import argparse
import csv
import datetime
import io
import json
import os
import statistics
import sys

import _bootstrap  # noqa: F401
from igkit import features as F, paths, report as R

ALIASES = {
    "url": ("url", "link", "permalink"),
    "account": ("account", "handle", "username", "creator"),
    "format": ("format", "type", "media_type", "post type"),
    "hook": ("hook", "first line", "opening", "hook_text", "caption"),
    "topic": ("topic", "theme", "subject"),
    "views": ("views", "plays", "video views", "reach"),
    "likes": ("likes", "like_count"),
    "comments": ("comments", "comments_count"),
    "shares": ("shares", "sends"),
    "saves": ("saves", "saved"),
    "posted": ("posted", "date", "published", "timestamp", "publish time"),
    "account_median_views": ("account_median_views", "median_views", "baseline", "account median"),
    "followers": ("followers", "follower_count"),
    "source": ("source", "collected_via"),
    "notes": ("notes", "note", "why"),
}
NUMERIC = ("views", "likes", "comments", "shares", "saves", "account_median_views", "followers")
MIN_DERIVED = 5


def parse_num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace(" ", "")
    if not s or s.lower() in ("na", "n/a", "-", "?", "none", "unknown"):
        return None
    mult = 1
    if s[-1] in "kK":
        mult, s = 1000, s[:-1]
    elif s[-1] in "mM":
        mult, s = 1000000, s[:-1]
    elif s[-1] in "bB":
        mult, s = 1000000000, s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def load_rows(path):
    raw = paths.read_text(path)
    if path.endswith(".json") or raw.lstrip().startswith("["):
        data = json.loads(raw)
    else:
        data = list(csv.DictReader(io.StringIO(raw)))
    rows = []
    for d in data:
        low = {str(k).strip().lower(): v for k, v in d.items() if k is not None}
        row = {}
        for field, names in ALIASES.items():
            val = next((low[n] for n in names if n in low and str(low[n]).strip() != ""), None)
            row[field] = parse_num(val) if field in NUMERIC else (str(val).strip() if val is not None else None)
        rows.append(row)
    return rows


def analyse(rows, min_multiple=2.0):
    formulas = paths.load_config("hook_formulas")["formulas"]
    by_acct = {}
    for r in rows:
        if r["account"] and r["views"] is not None:
            by_acct.setdefault(r["account"].lower(), []).append(r["views"])
    for r in rows:
        r["formula"] = (F.match_formulas(r["hook"], formulas) or ["unclassified"])[0] if r["hook"] else "no hook text"
        acct = (r["account"] or "").lower()
        if r["account_median_views"]:
            r["baseline"], r["baseline_source"] = r["account_median_views"], "provided"
        elif acct and len(by_acct.get(acct, [])) >= MIN_DERIVED:
            r["baseline"] = statistics.median(by_acct[acct])
            r["baseline_source"] = "derived (n=%d)" % len(by_acct[acct])
        else:
            r["baseline"], r["baseline_source"] = None, "none"
        r["multiple"] = round(r["views"] / r["baseline"], 2) if (r["views"] is not None and r["baseline"]) else None
        present = [k for k in ("likes", "comments", "shares", "saves") if r[k] is not None]
        if r["views"] and present:
            r["interaction_rate"] = round(sum(r[k] for k in present) / r["views"], 4)
            r["interaction_fields"] = present
        else:
            r["interaction_rate"], r["interaction_fields"] = None, present
        r["missing"] = [k for k in ("views", "likes", "comments", "shares", "saves") if r[k] is None]

    ranked = sorted([r for r in rows if r["multiple"] is not None], key=lambda r: r["multiple"], reverse=True)
    unranked = [r for r in rows if r["multiple"] is None]

    def group(key):
        g = {}
        for r in rows:
            g.setdefault(r.get(key) or "unknown", []).append(r)
        out = []
        for k, items in g.items():
            mults = [i["multiple"] for i in items if i["multiple"] is not None]
            out.append({
                key: k, "count": len(items), "with_baseline": len(mults),
                "median_multiple": round(statistics.median(mults), 2) if mults else None,
                "outliers": sum(1 for m in mults if m >= min_multiple),
                "confidence": "low" if len(mults) < 3 else ("medium" if len(mults) < 8 else "higher"),
            })
        return sorted(out, key=lambda x: (x["median_multiple"] or -1, x["count"]), reverse=True)

    return {
        "summary": {
            "posts": len(rows), "ranked": len(ranked), "unranked": len(unranked),
            "accounts": len({(r["account"] or "").lower() for r in rows if r["account"]}),
            "min_multiple": min_multiple,
            "sources": sorted({r["source"] or "unspecified" for r in rows}),
        },
        "ranked": ranked, "unranked": unranked,
        "patterns": {"formula": group("formula"), "format": group("format"), "topic": group("topic")},
    }


def _n(v):
    if v is None:
        return "n/a"
    if v >= 1e6:
        return "%.1fM" % (v / 1e6)
    if v >= 1e3:
        return "%.1fK" % (v / 1e3)
    return "%g" % v


def to_markdown(res, niche=""):
    s = res["summary"]
    out = ["# Research log%s" % (": " + niche if niche else ""), "",
           "Built %s from %d posts across %d accounts. %d ranked against their own account baseline, %d unranked (no reliable baseline)."
           % (datetime.date.today().isoformat(), s["posts"], s["accounts"], s["ranked"], s["unranked"]), "",
           "> All metrics were supplied by the user (sources: %s) and are not independently verified. Missing values were left blank, never estimated." % ", ".join(s["sources"]),
           "", "## What is working (by hook formula)", "",
           "| formula | posts | with baseline | median multiple | outliers (>=%gx) | confidence |" % s["min_multiple"],
           "| --- | --- | --- | --- | --- | --- |"]
    for g in res["patterns"]["formula"]:
        out.append("| %s | %d | %d | %s | %d | %s |" % (g["formula"], g["count"], g["with_baseline"],
                                                    ("%.2fx" % g["median_multiple"]) if g["median_multiple"] else "n/a",
                                                    g["outliers"], g["confidence"]))
    out += ["", "## By format", "", "| format | posts | median multiple | confidence |", "| --- | --- | --- | --- |"]
    for g in res["patterns"]["format"]:
        out.append("| %s | %d | %s | %s |" % (g["format"], g["count"],
                                            ("%.2fx" % g["median_multiple"]) if g["median_multiple"] else "n/a", g["confidence"]))
    out += ["", "## Ranked posts", ""]
    for i, r in enumerate(res["ranked"], 1):
        out += ["### %d. %.2fx  @%s  (%s)" % (i, r["multiple"], r["account"] or "?", r["format"] or "format?"),
                "", "- Hook: \"%s\"" % (r["hook"] or "not recorded"),
                "- Formula: %s" % r["formula"],
                "- Views %s vs baseline %s (%s)" % (_n(r["views"]), _n(r["baseline"]), r["baseline_source"]),
                "- Topic: %s" % (r["topic"] or "not recorded"),
                "- Link: %s" % (r["url"] or "not recorded"),
                "- Why it worked: %s" % (r["notes"] or "_analysis to add_"),
                "- How to adapt it (own angle, own proof): _to add_", ""]
    if res["unranked"]:
        out += ["## Unranked (kept for hook reference only)", ""]
        for r in res["unranked"]:
            out.append("- @%s: \"%s\" (%s; views %s)" % (r["account"] or "?", r["hook"] or "no hook", r["formula"], _n(r["views"])))
    return "\n".join(out) + "\n"


def library_path():
    return os.path.join(paths.workspace_dir(), "research-library.json")


def save_to_library(rows):
    p = library_path()
    lib = paths.load_json(p) if os.path.isfile(p) else {"items": []}
    seen = {i.get("url") for i in lib["items"] if i.get("url")}
    added = 0
    for r in rows:
        if r.get("url") and r["url"] in seen:
            continue
        item = {k: r.get(k) for k in ("url", "account", "format", "hook", "topic", "formula", "views", "baseline",
                                      "baseline_source", "multiple", "notes", "source")}
        item["saved"] = datetime.date.today().isoformat()
        lib["items"].append(item)
        added += 1
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(lib, fh, indent=2, ensure_ascii=False)
    return p, added, len(lib["items"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?")
    ap.add_argument("--min-multiple", type=float, default=2.0, help="what counts as an outlier (default 2x)")
    ap.add_argument("--md", help="write the research log to this path")
    ap.add_argument("--niche", default="", help="title for the research log")
    ap.add_argument("--save", action="store_true", help="append to the reusable research library")
    ap.add_argument("--library", action="store_true", help="print the saved library")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.library:
        p = library_path()
        if not os.path.isfile(p):
            print("No library yet at %s (use --save)." % p)
            return 0
        lib = paths.load_json(p)
        if args.json:
            R.emit_json(lib)
        else:
            print(R.table([(i.get("formula"), i.get("multiple") or "n/a", "@%s" % i.get("account"), (i.get("hook") or "")[:50])
                           for i in lib["items"]], ["formula", "multiple", "account", "hook"]))
        return 0
    if not args.file:
        ap.error("give an observations file, or --library")

    res = analyse(load_rows(args.file), args.min_multiple)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(res, args.niche))
    if args.save:
        p, added, total = save_to_library(res["ranked"] + res["unranked"])
    if args.json:
        R.emit_json(res)
        return 0
    s = res["summary"]
    print("RESEARCH LOG  %d posts, %d accounts, %d ranked, %d unranked" % (s["posts"], s["accounts"], s["ranked"], s["unranked"]))
    print("=" * 78)
    if res["ranked"]:
        print(R.table([("%.2fx" % r["multiple"], "@%s" % r["account"], r["format"] or "?", r["formula"],
                        r["baseline_source"], (r["hook"] or "")[:34]) for r in res["ranked"]],
                      ["multiple", "account", "format", "formula", "baseline", "hook"]))
    else:
        print("No post has a reliable baseline. Add account_median_views, or 5+ posts per account with views.")
    print("\nPATTERNS BY FORMULA")
    print(R.table([(g["formula"], g["count"], g["with_baseline"], ("%.2fx" % g["median_multiple"]) if g["median_multiple"] else "n/a",
                    g["outliers"], g["confidence"]) for g in res["patterns"]["formula"]],
                  ["formula", "posts", "baselined", "median", ">=%gx" % s["min_multiple"], "confidence"]))
    missing = sorted({m for r in res["ranked"] + res["unranked"] for m in r["missing"]})
    if missing:
        print("\nNot in the data for some posts (left blank, not estimated): " + ", ".join(missing))
    print("Metrics are user-supplied (%s), not independently verified." % ", ".join(s["sources"]))
    if args.md:
        print("Research log written: " + args.md)
    if args.save:
        print("Library: %s (+%d, %d total)" % (p, added, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
