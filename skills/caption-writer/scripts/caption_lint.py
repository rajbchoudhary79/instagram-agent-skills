#!/usr/bin/env python3
"""Preview a caption the way the feed shows it, then lint and score it.

  caption_lint.py caption.txt
  caption_lint.py caption.txt --keywords "sourdough starter,beginner sourdough"
  caption_lint.py caption.txt --window 100            test a tighter preview
  caption_lint.py captions.txt --split blocks         compare variants separated by ---
  pbpaste | caption_lint.py -

Checks come from config/platform.json (limits, with confidence levels) and the
caption + engagement rubrics. Exit 0 READY, 1 REVIEW, 2 BLOCKED.
"""

import argparse
import re
import sys

import _bootstrap  # noqa: F401
from igkit import cli, engine, lexicon as L, paths, report as R, text as T


def lint(caption, ctx, window=None):
    plat = paths.load_config("platform")["caption"]
    limit = plat["max_chars"]["value"]
    vis_n = window or plat["visible_chars"]["value"]
    tag_cap = plat["max_hashtags"]["value"]
    generic = {g.lower() for g in L.lexicon()["generic_hashtags"]}
    checks = []

    def add(level, cid, msg):
        checks.append({"level": level, "id": cid, "message": msg})

    n = len(caption)
    add("FAIL" if n > limit else "PASS", "length", "%d / %d characters" % (n, limit))

    visible, truncated = T.truncate_visible(caption, vis_n)
    first = T.first_line(caption)
    if L.starts_with_any(first, "greetings"):
        add("FAIL", "greeting", "Line one opens with a greeting.")
    if first.startswith("#"):
        add("FAIL", "hashtag_first", "Line one starts with a hashtag.")
    if T.starts_with_emoji(first):
        add("WARN", "emoji_first", "Line one starts with an emoji.")
    if len(first) > vis_n:
        add("WARN", "first_line_cut", "Line one is %d characters, so the feed cuts it mid-thought at ~%d." % (len(first), vis_n))
    else:
        add("PASS", "first_line", "Line one fits the visible window (%d of ~%d)." % (len(first), vis_n))

    tags = T.hashtags(caption)
    if len(tags) > tag_cap:
        add("FAIL", "hashtag_count", "%d hashtags; cap is %d (confidence: %s)." % (len(tags), tag_cap, plat["max_hashtags"]["confidence"]))
    else:
        add("PASS", "hashtag_count", "%d hashtag(s), cap %d." % (len(tags), tag_cap))
    gen = [t for t in tags if t.lower() in generic]
    if gen:
        add("WARN", "generic_tags", "Generic tags that describe nothing: " + ", ".join("#" + g for g in gen))
    body_lines = [ln for ln in caption.splitlines() if ln.strip()]
    if tags and body_lines and not all(w.startswith("#") for w in body_lines[-1].split()):
        mid = [t for t in tags if "#" + t in " ".join(body_lines[:-1])]
        if mid:
            add("INFO", "tag_position", "Hashtags inside the body. Fine if they read as words; otherwise move them to the last line.")

    links = T.links(caption)
    if links:
        add("WARN", "link", "Caption links are not clickable: %s. Use bio, a story link sticker or a keyword DM." % ", ".join(links))

    asks = L.asks(caption)
    if not asks:
        add("WARN", "no_ask", "No call to action found. Fine for pure community posts; otherwise add one.")
    elif len(asks) > 1:
        add("WARN", "many_asks", "%d different asks (%s). Keep one." % (len(asks), ", ".join(asks)))
    else:
        add("PASS", "ask", "One ask: %s." % asks[0])
    if "comment" in asks:
        kw = re.findall(r"\b[A-Z]{2,}\b", caption)
        if kw and any(" " in k for k in kw):
            add("WARN", "keyword", "The comment keyword should be one word.")

    kws = ctx.get("keywords") or []
    if kws:
        low = caption.lower()
        missing = [k for k in kws if k.lower() not in low]
        in_vis = [k for k in kws if k.lower() in visible.lower()]
        src = " (from profile)" if ctx.get("keywords_from_profile") else ""
        if missing:
            add("WARN", "keywords", "Search phrases missing%s: %s" % (src, ", ".join(missing)))
        else:
            add("PASS", "keywords", "All search phrases present%s." % src)
        if not in_vis:
            add("INFO", "keyword_visible", "No search phrase in the visible window.")

    e_rate = 100.0 * T.emoji_count(caption) / n if n else 0
    if e_rate > 4:
        add("WARN", "emoji", "%.1f emoji per 100 characters. Use them as punctuation, not wallpaper." % e_rate)

    for para in re.split(r"\n\s*\n", caption):
        if len(para) > 400:
            add("WARN", "wall", "A paragraph runs %d characters without a break. Phones show that as a wall." % len(para))
            break

    slop = L.slop_hits(caption)
    if slop:
        add("WARN", "slop", "Slop: " + ", ".join(t for t, _ in slop) + ". Run content-humanizer.")
    if L.invisible_chars(caption):
        add("FAIL", "invisible", "Invisible characters present. Run content-humanizer clean.")
    if len(T.mentions(caption)) > plat["max_mentions"]["value"]:
        add("FAIL", "mentions", "Too many @mentions.")

    return {"visible": visible, "truncated": truncated, "hidden_chars": max(0, n - len(visible)),
            "checks": checks, "verdict": R.verdict(checks)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="path to the caption text ('-' reads stdin)")
    ap.add_argument("--window", type=int, help="visible window in characters (default from platform.json)")
    ap.add_argument("--split", choices=["none", "blocks"], default="none", help="several variants separated by ---")
    cli.add_common(ap)
    args = ap.parse_args(argv)
    ctx, prof = cli.build_ctx(args)
    ctx["visible"] = args.window or paths.load_config("platform")["caption"]["visible_chars"]["value"]
    raw = paths.read_text(args.file)
    if args.split == "blocks":
        variants = [v for v in re.split(r"\n\s*---+\s*\n", raw.strip()) if v.strip()]
    else:
        variants = [raw.strip("\n")]

    results = []
    for v in variants:
        res = lint(v, ctx, args.window)
        res["caption_score"] = engine.score(v, "caption", ctx)
        res["engagement_score"] = engine.score(v, "engagement", ctx)
        res["text"] = v
        results.append(res)

    if args.json:
        R.emit_json({"profile": prof, "keywords": ctx.get("keywords"), "results": results})
    else:
        for i, res in enumerate(results):
            if len(results) > 1:
                print("\n#### VARIANT %d" % (i + 1))
            print(R.box(res["visible"] + (" ... more" if res["truncated"] else ""), width=64,
                        title="WHAT THE FEED SHOWS (~%d chars)" % ctx["visible"]))
            if res["truncated"]:
                print("  + %d more characters behind the tap" % res["hidden_chars"])
            print()
            print(R.render_checks(res["checks"]))
            cs, es = res["caption_score"], res["engagement_score"]
            print()
            print("  caption quality     %5.1f %-6s weakest: %s" % (cs["score"], cs["band"], cs["weakest"]))
            print("  engagement signals  %5.1f %-6s weakest: %s" % (es["score"], es["band"], es["weakest"]))
            print("  (heuristics: structure, not a reach prediction. Full reasons: core.py score --rubric caption)")
            print("VERDICT: %s" % res["verdict"])
        if len(results) > 1:
            best = max(range(len(results)), key=lambda i: results[i]["caption_score"]["score"])
            print("\nHighest caption score: variant %d" % (best + 1))
    worst = max(({"READY": 0, "REVIEW": 1, "BLOCKED": 2}[r["verdict"]] for r in results))
    return worst


if __name__ == "__main__":
    sys.exit(main())
