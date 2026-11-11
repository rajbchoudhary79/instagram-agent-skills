#!/usr/bin/env python3
"""Validate a carousel spec, score it, and export a production spec sheet and SVG slides.

  carousel.py spec.json                       validate + score
  carousel.py spec.json --md spec.md          write the designer / Canva spec sheet
  carousel.py spec.json --svg out_dir/        render 1080x1350 SVG slides (simple type-only layout)
  carousel.py spec.json --json

Spec format (JSON):
  {
    "title": "Feed in the morning, bake after work",
    "theme": {"bg": "#F5F1EA", "fg": "#1F1F1F", "accent": "#E4572E", "font": "Inter"},   (optional)
    "slides": [
      {"role": "cover", "headline": "...", "body": "", "visual": "...", "alt": "..."},
      {"role": "point", "headline": "...", "body": "...", "visual": "...", "alt": "..."},
      {"role": "cta", "headline": "...", "body": "Comment STARTER ..."}
    ]
  }
Roles: see carousel.json. Theme falls back to profile visual.colors / fonts.
The SVGs are a type-only layout for review or as a base layer, not final design.
Exit 0 READY, 1 REVIEW, 2 BLOCKED.
"""

import argparse
import json
import os
import re
import sys
import textwrap
from xml.sax.saxutils import escape

import _bootstrap  # noqa: F401
from igkit import cli, engine, features as F, lexicon as L, paths, profile as P, report as R, text as T

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rules():
    return paths.load_json(os.path.join(HERE, "carousel.json"))


def slide_text(s):
    return "\n".join(x for x in (s.get("headline", ""), s.get("body", "")) if x)


def validate(spec, ctx):
    cfg = rules()
    plat = paths.load_config("platform")["carousel"]
    checks = []

    def add(level, cid, msg, slide=None):
        checks.append({"level": level, "id": cid, "slide": slide, "message": msg})

    slides = spec.get("slides") or []
    n = len(slides)
    lo, hi = plat["min_slides"]["value"], plat["max_slides"]["value"]
    if not lo <= n <= hi:
        add("FAIL", "count", "%d slides; Instagram allows %d-%d." % (n, lo, hi))
    else:
        rlo, rhi = cfg["recommended_slides"]
        add("PASS" if rlo <= n <= rhi else "INFO", "count",
            "%d slides%s." % (n, "" if rlo <= n <= rhi else " (most carousels land between %d and %d)" % (rlo, rhi)))
    if not slides:
        return checks, None

    for i, s in enumerate(slides, 1):
        role = s.get("role", "")
        if role and role not in cfg["roles"]:
            add("WARN", "role", "Unknown role '%s'." % role, i)
        if not slide_text(s).strip() and not s.get("visual"):
            add("FAIL", "empty", "Slide is empty.", i)
        hw, bw = T.word_count(s.get("headline", "")), T.word_count(s.get("body", ""))
        if i > 1 and hw > cfg["headline_max_words"]:
            add("WARN", "headline_long", "Headline is %d words (max %d)." % (hw, cfg["headline_max_words"]), i)
        if bw > cfg["body_max_words"]:
            add("WARN", "body_long", "Body is %d words (max %d). Split the slide." % (bw, cfg["body_max_words"]), i)
        if not s.get("alt"):
            add("INFO", "alt", "No alt text.", i)
        if L.invisible_chars(slide_text(s)):
            add("FAIL", "invisible", "Invisible characters.", i)

    cover = slides[0]
    if cover.get("role") not in (None, "", "cover"):
        add("WARN", "cover_role", "First slide is not a cover.", 1)
    ch = cover.get("headline", "")
    if T.word_count(ch) > cfg["cover_max_words"] or len(ch) > cfg["cover_max_chars"]:
        add("WARN", "cover_long", "Cover headline is %d words / %d chars (max %d / %d). It has to read in one glance."
            % (T.word_count(ch), len(ch), cfg["cover_max_words"], cfg["cover_max_chars"]), 1)
    hook = engine.score(ch, "hook", dict(ctx, formulas=paths.load_config("hook_formulas")["formulas"])) if ch else None
    if hook:
        add("PASS" if hook["score"] >= 65 else "WARN", "cover_hook",
            "Cover as a hook: %.0f %s (weakest: %s)." % (hook["score"], hook["band"], hook["weakest"]), 1)

    last = slides[-1]
    if not (last.get("role") == "cta" or L.asks(slide_text(last))):
        add("WARN", "no_cta", "Last slide has no ask. Tell them what to do: save, share, comment a keyword.", n)

    nums = [int(m.group(1)) for s in slides if (m := re.match(r"\s*(\d{1,2})[.)]", s.get("headline", "")))]
    if nums and nums != list(range(nums[0], nums[0] + len(nums))):
        add("WARN", "numbering", "Numbered headlines skip or repeat: %s." % nums)

    vocab = [{w for w in T.lower_words(slide_text(s)) if len(w) > 3 and w not in F.STOP} for s in slides]
    for i in range(1, n - 1):
        others = set().union(*(vocab[j] for j in range(n) if j != i))
        if vocab[i] and not (vocab[i] & others):
            add("WARN", "continuity", "Shares no key words with any other slide. Check it belongs in this story.", i + 1)
    return checks, hook


def theme_for(spec, profile):
    th = dict(rules()["render"]["default_theme"])
    colors = P.get(profile or {}, "visual.colors") or []
    fonts = P.get(profile or {}, "visual.fonts") or []
    for key, val in zip(("bg", "fg", "accent"), colors):
        th[key] = val
    if fonts:
        th["font"] = "%s, Helvetica, Arial, sans-serif" % fonts[0]
    th.update(spec.get("theme") or {})
    return th


def wrap(text, px, width, ratio):
    max_chars = max(8, int(width / (px * ratio)))
    out = []
    for para in text.split("\n"):
        out.extend(textwrap.wrap(para, max_chars) or [""])
    return out


def render_svg(slide, idx, total, theme, cfg):
    r = cfg["render"]
    W, H, M = r["width"], r["height"], r["margin"]
    inner = W - 2 * M
    hp = r["cover_px"] if idx == 1 else r["headline_px"]
    bp = r["body_px"]
    lh = r["line_height"]
    hl = wrap(slide.get("headline", ""), hp, inner, r["char_width_ratio"])
    bl = wrap(slide.get("body", ""), bp, inner, r["char_width_ratio"]) if slide.get("body") else []
    block = len(hl) * hp * lh + (bp if bl else 0) + len(bl) * bp * lh
    y = max(M + hp, (H - block) / 2 + hp) if idx == 1 else M + hp + 40
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, H, W, H),
             '<rect width="100%%" height="100%%" fill="%s"/>' % escape(theme["bg"]),
             '<rect x="%d" y="%d" width="96" height="10" fill="%s"/>' % (M, M - 40, escape(theme["accent"]))]
    for ln in hl:
        parts.append('<text x="%d" y="%d" font-family="%s" font-size="%d" font-weight="700" fill="%s">%s</text>'
                     % (M, y, escape(theme["font"]), hp, escape(theme["fg"]), escape(ln)))
        y += hp * lh
    if bl:
        y += bp
        for ln in bl:
            parts.append('<text x="%d" y="%d" font-family="%s" font-size="%d" fill="%s">%s</text>'
                         % (M, y, escape(theme["font"]), bp, escape(theme["fg"]), escape(ln)))
            y += bp * lh
    parts.append('<text x="%d" y="%d" font-family="%s" font-size="28" fill="%s" text-anchor="end">%d/%d</text>'
                 % (W - M, H - M / 2, escape(theme["font"]), escape(theme["fg"]), idx, total))
    parts.append("</svg>")
    overflow = y > H - M
    return "\n".join(parts), overflow


def to_markdown(spec, theme, checks):
    out = ["# Carousel spec: %s" % spec.get("title", "untitled"), "",
           "- Size: 1080 x 1350 px (4:5). All slides share the cover's aspect ratio.",
           "- Grid: the profile grid shows a 3:4 crop of the cover; keep the headline centred.",
           "- Colours: background %s, text %s, accent %s" % (theme["bg"], theme["fg"], theme["accent"]),
           "- Font: %s" % theme["font"], "- Margins: 96 px all sides; slide number bottom right.", ""]
    for i, s in enumerate(spec["slides"], 1):
        out += ["## Slide %d: %s" % (i, s.get("role", "")), "",
                "**Headline:** %s" % (s.get("headline") or "_none_"), ""]
        if s.get("body"):
            out += ["**Body:** %s" % s["body"], ""]
        out += ["**Visual:** %s" % (s.get("visual") or "type only"),
                "**Alt text:** %s" % (s.get("alt") or "_add alt text_"), ""]
        notes = [c["message"] for c in checks if c.get("slide") == i and c["level"] in ("WARN", "FAIL")]
        if notes:
            out += ["> Fix: " + " ".join(notes), ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="carousel spec JSON")
    ap.add_argument("--md", help="write a spec sheet")
    ap.add_argument("--svg", help="directory for SVG slides")
    cli.add_common(ap, keywords=False)
    args = ap.parse_args(argv)
    ctx, prof = cli.build_ctx(args, use_profile_keywords=False)
    try:
        spec = json.loads(paths.read_text(args.spec))
    except ValueError as exc:
        print("BLOCKED: spec is not valid JSON (%s)" % exc)
        return 2
    checks, hook = validate(spec, ctx)
    slides = spec.get("slides") or []
    full = "\n".join(slide_text(s) for s in slides)
    story = engine.score(full, "storytelling", ctx) if full.strip() else None
    human = engine.score(full, "human", ctx) if full.strip() else None
    theme = theme_for(spec, ctx.get("profile"))

    written = []
    if args.svg and slides:
        os.makedirs(args.svg, exist_ok=True)
        for i, s in enumerate(slides, 1):
            svg, overflow = render_svg(s, i, len(slides), theme, rules())
            p = os.path.join(args.svg, "slide_%02d.svg" % i)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(svg)
            written.append(p)
            if overflow:
                checks.append({"level": "WARN", "id": "overflow", "slide": i, "message": "Text overflows the slide at this type size."})
    if args.md and slides:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(spec, theme, checks))

    verdict = R.verdict(checks)
    if args.json:
        R.emit_json({"verdict": verdict, "checks": checks, "cover_hook": hook and hook["score"],
                     "storytelling": story and story["score"], "human": human and human["score"],
                     "theme": theme, "svg": written, "md": args.md})
    else:
        print("CAROUSEL  %s  (%d slides)" % (spec.get("title", "untitled"), len(slides)))
        print("=" * 78)
        for c in checks:
            where = ("slide %d: " % c["slide"]) if c.get("slide") else ""
            print("  %-5s %s%s" % (c["level"], where, c["message"]))
        if story:
            print("\n  storytelling  %5.1f %-6s weakest: %s" % (story["score"], story["band"], story["weakest"]))
            print("  human         %5.1f %-6s weakest: %s" % (human["score"], human["band"], human["weakest"]))
        if written:
            print("\n  SVG slides: %s (%d files)" % (args.svg, len(written)))
        if args.md:
            print("  Spec sheet: %s" % args.md)
        print("VERDICT: %s" % verdict)
    return {"READY": 0, "REVIEW": 1, "BLOCKED": 2}[verdict]


if __name__ == "__main__":
    sys.exit(main())
