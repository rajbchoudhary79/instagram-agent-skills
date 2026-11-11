#!/usr/bin/env python3
"""Publish an approved post to Instagram through the official API.

Nothing goes live without an approval code: `check` validates the post, runs the
quality gate on the caption and prints a code tied to the exact content.
`publish` only runs with that code, and refuses if anything changed since.

  publish.py check post.json                    validate + gate; prints the approval code (offline)
  publish.py publish post.json --approve CODE   publish (needs IG_ACCESS_TOKEN)
  publish.py publish post.json --approve CODE --dry-run    show the API calls, send nothing
  publish.py account                            whose token this is + publishing quota (read-only)
  publish.py log                                what has been published from this machine

post.json:
  {"type": "image" | "carousel" | "reel" | "story",
   "caption": "..."  or  "caption_file": "caption.txt"   (relative to post.json),
   "media": [{"url": "https://.../1.jpg", "kind": "image", "alt_text": "..."},
             {"url": "https://.../clip.mp4", "kind": "video"}],
   "reel": {"cover_url": "https://...", "share_to_feed": true, "thumb_offset": 1500},
   "note": "anything, e.g. calendar item c-0003"}

Credentials (never passwords; never written to disk by this tool):
  IG_ACCESS_TOKEN        token from your own Meta app (or IG_ACCESS_TOKEN_FILE = path to a file holding it)
  IG_USER_ID             optional; looked up from the token if missing
  IG_API_HOST / IG_API_VERSION   optional overrides (see publisher.json)

Exit codes: 0 done/ready, 1 ready with warnings, 2 blocked/refused/API error, 3 no token.
"""

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.parse

import _bootstrap  # noqa: F401
from igkit import cli, paths, report as R, schema, text as T

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import igapi  # noqa: E402

TYPES = ("image", "carousel", "reel", "story")
POST_SCHEMA = {
    "type": "object",
    "required": ["type", "media"],
    "additionalProperties": False,
    "properties": {
        "type": {"type": "string", "enum": list(TYPES)},
        "caption": {"type": "string"},
        "caption_file": {"type": "string", "minLength": 1},
        "media": {"type": "array", "minItems": 1, "items": {
            "type": "object", "required": ["url", "kind"], "additionalProperties": False,
            "properties": {"url": {"type": "string", "minLength": 8},
                           "kind": {"type": "string", "enum": ["image", "video"]},
                           "alt_text": {"type": "string"}}}},
        "reel": {"type": "object", "additionalProperties": False, "properties": {
            "cover_url": {"type": "string"}, "share_to_feed": {"type": "boolean"},
            "thumb_offset": {"type": "integer", "minimum": 0}}},
        "note": {"type": "string"},
    },
}
PRIVATE_HOST_RE = re.compile(r"^(?:localhost|127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.|0\.0\.0\.0|\[?::1\]?)", re.I)


def config():
    return paths.load_json(os.path.join(SKILL_DIR, "publisher.json"))


def _val(entry):
    return entry["value"] if isinstance(entry, dict) and "value" in entry else entry


# -- loading and approval -------------------------------------------------------

def load_post(path):
    with open(path, encoding="utf-8") as fh:
        post = json.load(fh)
    caption = post.get("caption")
    if post.get("caption_file"):
        cpath = os.path.join(os.path.dirname(os.path.abspath(path)), post["caption_file"])
        with open(cpath, encoding="utf-8") as fh:
            caption = fh.read()
    return post, (caption or "").strip()


def approval_code(post, caption):
    """Short code tied to everything that would be sent. Any change -> new code."""
    canon = {"type": post.get("type"), "caption": caption, "media": post.get("media"), "reel": post.get("reel")}
    digest = hashlib.sha256(json.dumps(canon, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest().upper()
    return "%s-%s-%s" % (digest[:4], digest[4:8], digest[8:12])


# -- validation -----------------------------------------------------------------

def _ext(url):
    path = urllib.parse.urlsplit(url).path.lower()
    return path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else ""


def _load_gate():
    spec = importlib.util.spec_from_file_location("ig_gate", os.path.join(paths.CORE_DIR, "scripts", "gate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate(post, caption, ctx, cfg=None):
    cfg = cfg or config()
    lim = cfg["limits"]
    checks = []

    def add(level, cid, msg):
        checks.append({"id": cid, "level": level, "message": msg})

    errs = schema.validate(post, POST_SCHEMA)
    for e in errs:
        add("FAIL", "schema", e)
    if errs:
        return checks
    if "caption" in post and "caption_file" in post:
        add("FAIL", "caption_source", "Use caption or caption_file, not both.")
    ptype, media = post["type"], post["media"]
    kinds = [m["kind"] for m in media]

    # shape per type
    if ptype == "image" and kinds != ["image"]:
        add("FAIL", "shape", "An image post needs exactly one image.")
    elif ptype == "reel" and kinds != ["video"]:
        add("FAIL", "shape", "A reel needs exactly one video.")
    elif ptype == "story" and len(media) != 1:
        add("FAIL", "shape", "A story is one image or one video. Publish several frames as separate stories.")
    elif ptype == "carousel":
        lo, hi = _val(lim["carousel_min_items"]), _val(lim["carousel_max_items"])
        if not lo <= len(media) <= hi:
            add("FAIL", "shape", "A carousel needs %d-%d items (has %d)." % (lo, hi, len(media)))
    if "reel" in post and ptype != "reel":
        add("WARN", "reel_options", "'reel' options are ignored for a %s." % ptype)

    # media URLs: Meta fetches them, so they must be public and in a supported format
    img_ext, vid_ext = _val(lim["image_extensions"]), _val(lim["video_extensions"])
    urls = [(i, m["url"], m["kind"]) for i, m in enumerate(media, 1)]
    if post.get("reel", {}).get("cover_url"):
        urls.append(("cover", post["reel"]["cover_url"], "image"))
    for i, url, kind in urls:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            add("FAIL", "url", "Item %s: %r is not a web address. Instagram fetches media from a public URL; "
                               "upload the file somewhere public first." % (i, url))
            continue
        if PRIVATE_HOST_RE.match(parts.hostname):
            add("FAIL", "url", "Item %s: %s is a local/private address Instagram cannot reach." % (i, parts.hostname))
        elif parts.scheme != "https":
            add("WARN", "url", "Item %s: use an https:// URL." % i)
        ext = _ext(url)
        if kind == "image":
            if ext in img_ext:
                pass
            elif ext:
                add("FAIL", "format", "Item %s: .%s image. JPEG is the only image format Instagram's API accepts; "
                                      "export it as .jpg." % (i, ext))
            else:
                add("WARN", "format", "Item %s: no file extension; make sure the image is a JPEG." % i)
        elif kind == "video" and ext and ext not in vid_ext:
            add("WARN", "format", "Item %s: .%s video; MP4 or MOV is safest." % (i, ext))
    for i, m in enumerate(media, 1):
        if m.get("alt_text") and not (ptype == "image" and m["kind"] == "image"):
            add("INFO", "alt_text", "Item %d: alt text is only sent for single-image posts; add it in the app after posting." % i)

    # caption
    if ptype == "story":
        if caption:
            add("WARN", "caption", "Stories have no caption; it will not be sent.")
    else:
        if not caption:
            add("WARN", "caption", "No caption.")
        else:
            holes = T.placeholders(caption)
            if holes:
                add("FAIL", "placeholders", "Unfilled placeholders in the caption: %s. Fill them before publishing."
                    % ", ".join(sorted(set(holes))))
            gate = _load_gate().run_gate(caption, "caption", ctx)
            for c in gate["checks"]:
                if c["level"] in ("FAIL", "WARN") and c["id"] != "placeholders":
                    add(c["level"], "gate:" + c["id"], c["message"])
            add("INFO", "gate", "Caption gate verdict: %s." % gate["verdict"])
    if not any(c["level"] in ("FAIL", "WARN") for c in checks):
        add("PASS", "ready", "Post is valid for the %s endpoint." % ptype)
    return checks


# -- publishing -----------------------------------------------------------------

def container_requests(post, caption):
    """The container creation calls, in order. Carousel: children first, then the parent."""
    ptype, media = post["type"], post["media"]
    if ptype == "image":
        p = {"image_url": media[0]["url"]}
        if caption:
            p["caption"] = caption
        if media[0].get("alt_text"):
            p["alt_text"] = media[0]["alt_text"]
        return [("single", p)]
    if ptype == "reel":
        p = {"media_type": "REELS", "video_url": media[0]["url"]}
        if caption:
            p["caption"] = caption
        opts = post.get("reel", {})
        if "share_to_feed" in opts:
            p["share_to_feed"] = "true" if opts["share_to_feed"] else "false"
        if opts.get("cover_url"):
            p["cover_url"] = opts["cover_url"]
        if "thumb_offset" in opts:
            p["thumb_offset"] = str(opts["thumb_offset"])
        return [("single", p)]
    if ptype == "story":
        m = media[0]
        return [("single", {"media_type": "STORIES", ("image_url" if m["kind"] == "image" else "video_url"): m["url"]})]
    reqs = []
    for m in media:
        if m["kind"] == "image":
            reqs.append(("child", {"image_url": m["url"], "is_carousel_item": "true"}))
        else:
            reqs.append(("child", {"media_type": "VIDEO", "video_url": m["url"], "is_carousel_item": "true"}))
    parent = {"media_type": "CAROUSEL"}
    if caption:
        parent["caption"] = caption
    reqs.append(("parent", parent))
    return reqs


def publish_post(post, caption, client, ig_id, cfg, say=print):
    """Create containers, wait until they are ready, publish. Returns the result dict."""
    poll = cfg["polling"]
    child_ids, container = [], None
    for role, params in container_requests(post, caption):
        if role == "parent":
            params = dict(params, children=",".join(child_ids))
        cid = client.create_container(ig_id, params)
        say("  container %s created (%s)" % (cid, role))
        client.wait_until_ready(cid, poll["interval_seconds"], poll["attempts"])
        if role == "child":
            child_ids.append(cid)
        else:
            container = cid
    res = client.publish(ig_id, container)
    media_id = res.get("id")
    out = {"media_id": media_id, "container_id": container, "warnings": []}
    for key in ("config_issue", "caption_add_on_attachment_status"):
        if res.get(key):
            out["warnings"].append("%s: %s (published, but check the post in the app)" % (key, res[key]))
    try:
        out["permalink"] = client.permalink(media_id)
    except igapi.ApiError:
        out["permalink"] = None
    return out


def log_path():
    return os.path.join(paths.workspace_dir(), "publish-log.json")


def read_log():
    p = log_path()
    if not os.path.isfile(p):
        return {"published": []}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write_log(entry):
    data = read_log()
    data["published"].append(entry)
    os.makedirs(os.path.dirname(log_path()), exist_ok=True)
    with open(log_path(), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def get_token():
    tok = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not tok and os.environ.get("IG_ACCESS_TOKEN_FILE"):
        with open(os.path.expanduser(os.environ["IG_ACCESS_TOKEN_FILE"]), encoding="utf-8") as fh:
            tok = fh.read().strip()
    return tok


def make_client(cfg, transport=None):
    tok = get_token()
    if not tok:
        return None
    return igapi.Client(tok, os.environ.get("IG_API_HOST") or _val(cfg["api"]["host"]),
                        os.environ.get("IG_API_VERSION") or _val(cfg["api"]["version"]), transport=transport)


def resolve_ig_id(client):
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"], None
    me = client.me()
    return str(me.get("user_id") or me.get("id")), me.get("username")


NO_TOKEN = ("No access token. Set IG_ACCESS_TOKEN (or IG_ACCESS_TOKEN_FILE) to a token from your own Meta app "
            "with instagram_business_basic + instagram_business_content_publish. Never use your Instagram password. "
            "Setup steps: references/setup.md")


# -- commands -------------------------------------------------------------------

def cmd_check(args, ctx):
    post, caption = load_post(args.post)
    checks = validate(post, caption, ctx)
    verdict = R.verdict(checks)
    code = approval_code(post, caption)
    if args.json:
        R.emit_json({"verdict": verdict, "approval_code": code if verdict != "BLOCKED" else None,
                     "type": post.get("type"), "caption": caption, "media": post.get("media"), "checks": checks})
    else:
        print("PUBLISH PREVIEW  %s  (%d media item%s)" % (post.get("type"), len(post.get("media", [])),
                                                          "" if len(post.get("media", [])) == 1 else "s"))
        print("=" * 78)
        for i, m in enumerate(post.get("media", []), 1):
            print("  %2d. %-5s %s" % (i, m.get("kind"), m.get("url")))
        if caption and post.get("type") != "story":
            print(R.box(caption, width=74, title="caption, exactly as it will be posted"))
        print(R.render_checks(checks))
        print("-" * 78)
        print("VERDICT: %s" % verdict)
        if verdict == "BLOCKED":
            print("Fix the FAIL items; there is no approval code for a blocked post.")
        else:
            print("APPROVAL CODE: %s" % code)
            print("Nothing has been posted. To publish exactly this, the creator approves with this code:")
            print("  python3 scripts/publish.py publish %s --approve %s" % (args.post, code))
    return {"READY": 0, "REVIEW": 1, "BLOCKED": 2}[verdict]


def cmd_publish(args, ctx, transport=None, say=print):
    cfg = config()
    post, caption = load_post(args.post)
    checks = validate(post, caption, ctx, cfg)
    if R.verdict(checks) == "BLOCKED":
        say("REFUSED: the post is blocked. Run `publish.py check %s` and fix the FAIL items." % args.post)
        return 2
    code = approval_code(post, caption)
    if (args.approve or "").strip().upper() != code:
        say("REFUSED: approval code does not match this post (expected the code shown by `check`). "
            "If the post changed since it was approved, run check again and get a new approval.")
        return 2
    done = [e for e in read_log()["published"] if e.get("approval_code") == code]
    if done and not args.again:
        say("REFUSED: this exact post was already published on %s (%s). Use --again only if you really "
            "want a duplicate." % (done[-1]["at"], done[-1].get("permalink") or done[-1]["media_id"]))
        return 2
    if args.dry_run:
        say("DRY RUN: nothing will be sent.")
        for role, params in container_requests(post, caption):
            shown = {k: (v if k != "caption" else T.first_line(v)[:40] + "...") for k, v in params.items()}
            say("  POST /<IG_ID>/media  (%s)  %s" % (role, json.dumps(shown, ensure_ascii=False)))
        say("  POST /<IG_ID>/media_publish  creation_id=<container>")
        return 0
    client = make_client(cfg, transport)
    if client is None:
        say(NO_TOKEN)
        return 3
    try:
        ig_id, username = resolve_ig_id(client)
        say("Publishing to %s (account id %s) ..." % ("@" + username if username else "your account", ig_id))
        try:
            lim = client.publishing_limit(ig_id)
            row = (lim.get("data") or [{}])[0]
            used, total = row.get("quota_usage"), (row.get("config") or {}).get("quota_total")
            if used is not None and total and used >= total:
                say("REFUSED: publishing quota used up (%s of %s in the last 24 hours). Try later." % (used, total))
                return 2
            if used is not None:
                say("  quota: %s of %s used in the last 24 hours" % (used, total or "?"))
        except igapi.ApiError as e:
            say("  (could not read the publishing quota: %s; Instagram will still enforce it)" % e)
        result = publish_post(post, caption, client, ig_id, cfg, say)
    except igapi.ApiError as e:
        say("API ERROR: %s%s" % (e, " (code %s)" % e.code if e.code else ""))
        if e.code == 190:
            say("The token is invalid or expired. Generate a new one in your Meta app (references/setup.md).")
        say("Nothing was published unless a media id is shown above.")
        return 2
    entry = {"at": dt.datetime.now().isoformat(timespec="seconds"), "approval_code": code, "type": post["type"],
             "media_id": result["media_id"], "permalink": result.get("permalink"),
             "first_line": T.first_line(caption)[:80] if caption else "", "post_file": os.path.abspath(args.post),
             "note": post.get("note", "")}
    write_log(entry)
    say("PUBLISHED  media id %s" % result["media_id"])
    if result.get("permalink"):
        say("  %s" % result["permalink"])
    for w in result["warnings"]:
        say("  WARN %s" % w)
    say("Logged to %s" % log_path())
    return 0


def cmd_account(args):
    cfg = config()
    client = make_client(cfg)
    if client is None:
        print(NO_TOKEN)
        return 3
    try:
        ig_id, username = resolve_ig_id(client)
        lim = client.publishing_limit(ig_id)
    except igapi.ApiError as e:
        print("API ERROR: %s" % e)
        return 2
    row = (lim.get("data") or [{}])[0]
    info = {"account_id": ig_id, "username": username, "quota_usage": row.get("quota_usage"),
            "quota_total": (row.get("config") or {}).get("quota_total")}
    if args.json:
        R.emit_json(info)
    else:
        print("Token works for @%s (account id %s)." % (username or "?", ig_id))
        print("Published via API in the last 24 hours: %s of %s." % (info["quota_usage"], info["quota_total"] or "?"))
    return 0


def cmd_log(args):
    data = read_log()
    if args.json:
        R.emit_json(data)
        return 0
    if not data["published"]:
        print("Nothing published from this machine yet.")
        return 0
    print(R.table([[e["at"], e["type"], e["approval_code"], e.get("permalink") or e["media_id"], e.get("first_line", "")[:40]]
                   for e in data["published"]], ["when", "type", "approval", "link / id", "first line"]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="validate + gate; print the approval code (offline)")
    c.add_argument("post")
    cli.add_common(c)
    p = sub.add_parser("publish", help="publish an approved post")
    p.add_argument("post")
    p.add_argument("--approve", required=True, help="the approval code printed by check")
    p.add_argument("--dry-run", action="store_true", help="show the API calls without sending anything")
    p.add_argument("--again", action="store_true", help="allow publishing an identical post a second time")
    cli.add_common(p)
    a = sub.add_parser("account", help="check the token and publishing quota (read-only)")
    a.add_argument("--json", action="store_true")
    lg = sub.add_parser("log", help="what has been published from this machine")
    lg.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd in ("check", "publish"):
        ctx, _ = cli.build_ctx(args)
        return cmd_check(args, ctx) if args.cmd == "check" else cmd_publish(args, ctx)
    return cmd_account(args) if args.cmd == "account" else cmd_log(args)


if __name__ == "__main__":
    sys.exit(main())
