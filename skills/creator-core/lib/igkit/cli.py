"""Shared argparse options and context building for the CLI tools."""

import os

from . import paths, profile as P


def add_common(ap, keywords=True, refs=False, post=False):
    ap.add_argument("--profile", help="path to profile.json (default: auto-discovered)")
    ap.add_argument("--no-profile", action="store_true", help="ignore the creator profile")
    if keywords:
        ap.add_argument("--keywords", help="comma-separated search phrases (default: profile audience.search_terms)")
    if refs:
        ap.add_argument("--refs", nargs="*", default=[], help="reference text files to measure overlap against")
    if post:
        ap.add_argument("--post", help="the post / message being responded to: a file path or the text itself")
    ap.add_argument("--json", action="store_true", help="machine-readable output")


def _text_or_file(value):
    if value and os.path.isfile(value):
        return paths.read_text(value)
    return value


def build_ctx(args, use_profile_keywords=True):
    """Build the feature context from parsed args. Returns (ctx, profile_path_or_None)."""
    ctx = {}
    prof_path = None
    if not getattr(args, "no_profile", False):
        data, prof_path, errs = P.load(getattr(args, "profile", None))
        if data is not None:
            ctx["profile"] = data
        else:
            prof_path = None
    kw = getattr(args, "keywords", None)
    if kw:
        ctx["keywords"] = [k.strip() for k in kw.split(",") if k.strip()]
    elif use_profile_keywords and ctx.get("profile"):
        terms = P.get(ctx["profile"], "audience.search_terms") or []
        if terms:
            ctx["keywords"] = terms
            ctx["keywords_from_profile"] = True
    refs = getattr(args, "refs", None)
    if refs:
        ctx["refs"] = [paths.read_text(r) for r in refs]
    post = getattr(args, "post", None)
    if post:
        ctx["post"] = _text_or_file(post)
    return ctx, prof_path


def split_texts(raw, mode):
    """'lines': one text per non-empty line; 'blocks': separated by blank lines or '---'; 'none'."""
    if mode == "lines":
        return [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if mode == "blocks":
        import re
        parts = re.split(r"\n\s*(?:---+)?\s*\n", raw.strip())
        return [p.strip() for p in parts if p.strip()]
    return [raw.strip()]
