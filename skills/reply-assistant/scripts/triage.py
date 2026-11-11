#!/usr/bin/env python3
"""Sort the comments under a post into a reply queue.

  triage.py comments.txt                       one comment per line: "username: text" (or just text)
  triage.py comments.csv                        columns: username, text (or comment), likes (optional)
  triage.py comments.txt --keyword STARTER     the post's comment-keyword (default: profile goals.cta.keyword)
  triage.py comments.txt --json

Categories (categories.json, first match wins): spam, keyword, lead, support,
question, pushback, story, praise, tag, general. Priority decides reply order;
ties break on comment likes, then on order. This is a first pass: the reply
assistant reads every comment again before writing anything.
"""

import argparse
import csv
import io
import os
import re
import sys

import _bootstrap  # noqa: F401
from igkit import lexicon as L, paths, profile as P, report as R

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINE_RE = re.compile(r"^\s*@?([A-Za-z0-9_.]{1,30})\s*[:\-–]\s+(.+)$")


def load_comments(path):
    raw = paths.read_text(path)
    rows = []
    if path.endswith(".csv"):
        for d in csv.DictReader(io.StringIO(raw)):
            low = {k.strip().lower(): (v or "").strip() for k, v in d.items() if k}
            text = low.get("text") or low.get("comment") or ""
            if text:
                likes = low.get("likes") or "0"
                rows.append({"user": low.get("username") or low.get("user") or "", "text": text,
                             "likes": int(likes) if likes.isdigit() else 0})
        return rows
    for ln in raw.splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        m = LINE_RE.match(ln)
        if m:
            rows.append({"user": m.group(1), "text": m.group(2).strip(), "likes": 0})
        else:
            rows.append({"user": "", "text": ln.strip(), "likes": 0})
    return rows


def classify(text, cats, keyword=None):
    if keyword:
        kw_re = r"(?<![A-Za-z])" + re.escape(keyword) + r"(?![A-Za-z])"
        exact_case = re.search(r"(?<![A-Za-z])" + re.escape(keyword.upper()) + r"(?![A-Za-z])", text)
        rest = re.sub(kw_re, " ", text, flags=re.IGNORECASE)
        rest_words = re.findall(r"[A-Za-z]+", rest)
        if exact_case or (re.search(kw_re, text, re.IGNORECASE) and len(rest_words) <= 2):
            return "keyword", "matched keyword %s" % keyword
    for c in cats:
        if c["id"] in ("keyword", "general"):
            continue
        for p in c["patterns"]:
            if re.search(p, text, re.IGNORECASE):
                return c["id"], "pattern: %s" % p
    if L.is_generic_comment(text):
        return "praise", "generic positive"
    return "general", "no rule matched"


def triage(comments, keyword=None):
    cfg = paths.load_json(os.path.join(HERE, "categories.json"))["categories"]
    by_id = {c["id"]: c for c in cfg}
    out = []
    for n, c in enumerate(comments):
        cat, why = classify(c["text"], cfg, keyword)
        out.append(dict(c, n=n + 1, category=cat, priority=by_id[cat]["priority"], action=by_id[cat]["action"], why=why))
    queue = sorted(out, key=lambda x: (-x["priority"], -x["likes"], x["n"]))
    counts = {}
    for x in out:
        counts[x["category"]] = counts.get(x["category"], 0) + 1
    return queue, counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--keyword", help="comment keyword for this post")
    ap.add_argument("--profile")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    profile, _, _ = P.load(args.profile)
    keyword = args.keyword or P.get(profile or {}, "goals.cta.keyword") or None
    queue, counts = triage(load_comments(args.file), keyword)
    if args.json:
        R.emit_json({"keyword": keyword, "counts": counts, "queue": queue})
        return 0
    print("REPLY QUEUE  %d comments  keyword: %s" % (len(queue), keyword or "none"))
    print("  " + ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    print("=" * 78)
    print(R.table([(x["n"], x["category"], x["priority"], "@" + x["user"] if x["user"] else "", x["text"][:44], x["action"][:34])
                   for x in queue], ["#", "category", "pri", "user", "comment", "action"]))
    if counts.get("question", 0) >= 3:
        print("\n%d questions: consider answering the most common one as a reply reel." % counts["question"])
    print("\nFirst pass only. Read each comment before replying; categories can be wrong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
