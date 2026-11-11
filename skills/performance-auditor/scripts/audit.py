#!/usr/bin/env python3
"""Post-mortem on published content from an Insights / Business Suite export or a hand-made CSV.

  audit.py posts.csv
  audit.py posts.csv --rank-by saves_per_reach
  audit.py posts.csv --md audit.md
  audit.py posts.csv --json

Recognised columns (case-insensitive, common export names accepted):
  url/permalink, date/publish time, format/post type, caption/description, hook, pillar, topic,
  reach, impressions, views/plays, likes, comments, shares, saves, follows, profile visits,
  avg watch time (s), duration (s)

Rules: metrics that are not in the file are reported as missing and never
estimated. Rates use reach as the denominator when present (else views, and
the report says so). Group comparisons need at least 3 posts per group;
smaller groups are shown but marked too few to conclude.
"""

import argparse
import csv
import datetime as dt
import io
import re
import statistics
import sys

import _bootstrap  # noqa: F401
from igkit import features as F, paths, report as R, text as T

ALIASES = {
    "url": ("url", "permalink", "link", "post link"),
    "date": ("date", "publish time", "published", "posted", "timestamp", "publish_time"),
    "format": ("format", "post type", "type", "media type", "media_type"),
    "caption": ("caption", "description", "text"),
    "hook": ("hook", "first line"),
    "pillar": ("pillar", "content pillar"),
    "topic": ("topic", "title"),
    "reach": ("reach", "accounts reached"),
    "impressions": ("impressions",),
    "views": ("views", "plays", "video views"),
    "likes": ("likes", "reactions"),
    "comments": ("comments",),
    "shares": ("shares", "sends"),
    "saves": ("saves", "saved"),
    "follows": ("follows", "new follows", "follows from post"),
    "profile_visits": ("profile visits", "profile_visits", "profile activity"),
    "avg_watch": ("avg watch time", "average watch time", "avg_watch_seconds", "avg watch time (s)"),
    "duration": ("duration", "duration (sec)", "duration (s)", "length"),
}
METRICS = ("reach", "impressions", "views", "likes", "comments", "shares", "saves", "follows", "profile_visits", "avg_watch", "duration")
RATES = ("saves", "shares", "comments", "likes", "follows")
MIN_GROUP = 3


def num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if not s or s.lower() in ("na", "n/a", "-", "--"):
        return None
    m = re.match(r"^([\d.]+)\s*([kKmM])?$", s)
    if not m:
        mm = re.match(r"^(?:(\d+):)?(\d+):(\d{2})$", s)
        if mm:
            return int(mm.group(1) or 0) * 3600 + int(mm.group(2)) * 60 + int(mm.group(3))
        return None
    mult = {"k": 1e3, "m": 1e6}.get((m.group(2) or "").lower(), 1)
    return float(m.group(1)) * mult


def parse_date(s):
    if not s:
        return None
    s = s.strip().replace("Z", "")
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def load(path):
    raw = paths.read_text(path)
    rows = []
    for d in csv.DictReader(io.StringIO(raw.lstrip("﻿"))):
        low = {str(k).strip().lower(): v for k, v in d.items() if k is not None}
        r = {}
        for f, names in ALIASES.items():
            val = next((low[n] for n in names if n in low and str(low[n] or "").strip()), None)
            r[f] = num(val) if f in METRICS else (val.strip() if val else None)
        r["when"] = parse_date(r["date"])
        rows.append(r)
    return rows


def enrich(rows):
    formulas = paths.load_config("hook_formulas")["formulas"]
    use_reach = any(r["reach"] for r in rows)
    denom = "reach" if use_reach else "views"
    for r in rows:
        base = r[denom]
        for m in RATES:
            r[m + "_per_" + denom] = (r[m] / base) if (r[m] is not None and base) else None
        inter = [r[m] for m in ("likes", "comments", "shares", "saves") if r[m] is not None]
        r["engagement_rate"] = (sum(inter) / base) if (inter and base) else None
        r["watch_ratio"] = (r["avg_watch"] / r["duration"]) if (r["avg_watch"] and r["duration"]) else None
        hook = r["hook"] or (T.first_line(r["caption"]) if r["caption"] else None)
        r["hook_text"] = hook
        r["formula"] = (F.match_formulas(hook, formulas) or ["unclassified"])[0] if hook else "unknown"
        r["weekday"] = r["when"].strftime("%a") if r["when"] else None
        r["format"] = (r["format"] or "unknown").lower().replace("clips", "reel").replace("igtv", "video")
    vols = [r["views"] or r["reach"] for r in rows if (r["views"] or r["reach"])]
    med = statistics.median(vols) if vols else None
    for r in rows:
        v = r["views"] or r["reach"]
        r["multiple"] = (v / med) if (v and med) else None
    return denom, med


def coverage(rows):
    return {m: sum(1 for r in rows if r[m] is not None) for m in METRICS}


def group(rows, key, metric):
    g = {}
    for r in rows:
        g.setdefault(r.get(key) or "unknown", []).append(r)
    out = []
    for k, items in g.items():
        vals = [i[metric] for i in items if i[metric] is not None]
        out.append({key: k, "n": len(items), "n_metric": len(vals),
                    "median": statistics.median(vals) if vals else None,
                    "enough": len(vals) >= MIN_GROUP})
    return sorted(out, key=lambda x: (x["median"] is not None, x["median"] or 0), reverse=True)


def pick_metric(rows, denom, wanted):
    if wanted:
        return wanted
    for m in ("shares_per_" + denom, "saves_per_" + denom, "engagement_rate", "multiple"):
        if sum(1 for r in rows if r.get(m) is not None) >= max(3, len(rows) // 2):
            return m
    return "multiple"


def fmtv(metric, v):
    if v is None:
        return "n/a"
    if metric.endswith(("_per_reach", "_per_views")) or metric in ("engagement_rate", "watch_ratio"):
        return "%.2f%%" % (100 * v)
    if metric == "multiple":
        return "%.2fx" % v
    return "%g" % round(v, 1)


def findings(groups, metric):
    out = []
    for key, rows in groups.items():
        ok = [g for g in rows if g["enough"] and g["median"] is not None]
        if len(ok) >= 2:
            hi, lo = ok[0], ok[-1]
            if lo["median"] and hi["median"] / lo["median"] >= 1.3:
                out.append("By %s: '%s' has a median %s of %s vs %s for '%s' (n=%d vs %d)." % (
                    key, hi[key], metric, fmtv(metric, hi["median"]), fmtv(metric, lo["median"]), lo[key], hi["n_metric"], lo["n_metric"]))
        thin = [g[key] for g in rows if not g["enough"]]
        if thin:
            out.append("By %s: too few posts to compare %s (under %d each)." % (key, ", ".join(map(str, thin[:6])), MIN_GROUP))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--rank-by", help="metric to rank by, e.g. saves_per_reach, shares_per_reach, engagement_rate, multiple, watch_ratio")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--md")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rows = load(args.file)
    if not rows:
        print("No rows found.")
        return 1
    denom, med = enrich(rows)
    cov = coverage(rows)
    metric = pick_metric(rows, denom, args.rank_by)
    ranked = sorted([r for r in rows if r.get(metric) is not None], key=lambda r: r[metric], reverse=True)
    groups = {k: group(rows, k, metric) for k in ("format", "pillar", "formula", "weekday")}
    finds = findings(groups, metric)
    missing = [m for m, n in cov.items() if n == 0]
    if not any(cov[m] for m in ("avg_watch",)):
        missing_note = "Retention / watch time: not in the data. Nothing here speaks to retention."
    else:
        missing_note = ""

    if args.json:
        R.emit_json({"posts": len(rows), "denominator": denom, "median_volume": med, "rank_by": metric, "coverage": cov,
                     "missing": missing, "top": ranked[: args.top], "bottom": ranked[-args.top:][::-1] if len(ranked) > args.top else [],
                     "groups": groups, "findings": finds})
        return 0

    lines = []
    lines.append("CONTENT AUDIT  %d posts  rates per %s  ranked by %s" % (len(rows), denom, metric))
    lines.append("=" * 78)
    lines.append("Data coverage (posts with each metric): " + ", ".join("%s %d" % (m, n) for m, n in cov.items() if n))
    if missing:
        lines.append("Missing entirely (not estimated): " + ", ".join(missing))
    if missing_note:
        lines.append(missing_note)
    if denom == "views":
        lines.append("No reach column: rates use views as the denominator, which overstates reach for replays.")
    lines.append("")
    lines.append("TOP %d" % min(args.top, len(ranked)))
    lines.append(R.table([(fmtv(metric, r[metric]), r["format"], r["pillar"] or "", r["formula"], (r["hook_text"] or "")[:40])
                          for r in ranked[: args.top]], [metric, "format", "pillar", "formula", "hook"]))
    if len(ranked) > args.top:
        lines.append("")
        lines.append("BOTTOM %d" % min(args.top, len(ranked) - args.top))
        lines.append(R.table([(fmtv(metric, r[metric]), r["format"], r["pillar"] or "", r["formula"], (r["hook_text"] or "")[:40])
                              for r in ranked[-args.top:][::-1]], [metric, "format", "pillar", "formula", "hook"]))
    for key in ("format", "pillar", "formula"):
        lines.append("")
        lines.append("BY %s" % key.upper())
        lines.append(R.table([(g[key], g["n"], fmtv(metric, g["median"]), "" if g["enough"] else "too few")
                              for g in groups[key]], [key, "n", "median " + metric, ""]))
    lines.append("")
    lines.append("PATTERNS (descriptive, from this data only; correlation, not cause)")
    lines.extend("  - " + f for f in finds or ["No group difference large enough (>=1.3x with 3+ posts each) to report."])
    out = "\n".join(lines)
    print(out)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write("```\n" + out + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
