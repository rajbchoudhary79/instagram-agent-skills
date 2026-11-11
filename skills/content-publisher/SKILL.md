---
name: content-publisher
description: >-
  Publish a finished, creator-approved post to Instagram through Meta's official
  content-publishing API: image posts, carousels (up to 20 items), reels and
  stories. Validates the post and gates the caption offline, shows an exact
  preview with an approval code, and publishes only when the creator gives that
  code back. Uses the creator's own API token, never a password; never posts on
  its own, on a schedule, or twice. Use when the user says "post this",
  "publish to Instagram", "upload this carousel", "put this reel live", "check
  my Instagram API token", or "what have I published".
---

# Content publisher

The last step of the pipeline: an approved draft goes live, through the official
API, after the creator explicitly confirms that exact post.

## When to use

- A draft is final (gated READY or REVIEW with warnings accepted) and the media is exported and hosted.
- The creator wants to check their API setup or publishing quota.
- Not for drafting: send the creator to the writing skills first. Not for comments, replies or DMs: those are never automated.

## Inputs

### Required
- The approved caption (from caption-writer) and the media as **public HTTPS URLs**: JPEG for images, MP4/MOV for video. Instagram fetches the files itself; local files cannot be sent.
- An access token from the creator's own Meta app in `IG_ACCESS_TOKEN` (setup: `references/setup.md`). Only needed to publish or to check the account, not for `check`.

### Optional
- Alt text for a single image, reel cover URL, `share_to_feed`, `thumb_offset`.
- The content-planner item id, so the calendar can be updated afterwards.

## Workflow

1. Read the profile: `python3 scripts/core.py profile show`. The caption gate uses it (banned words, verified facts).
2. Write `post.json` (format: `python3 scripts/publish.py --help`; examples in `examples/`). Use the caption exactly as approved. Never invent media URLs: ask the creator for them. Carousel slides from carousel-creator are SVG; they must be exported to JPEG first.
3. Validate offline: `python3 scripts/publish.py check post.json`. Fix every FAIL (unverified claims, unfilled `{{placeholders}}`, non-JPEG images, local paths).
4. Show the creator the preview exactly as printed: media list, full caption, warnings, approval code. Ask: "Publish this now? Reply with the approval code to confirm."
5. Publish only after the creator's reply contains that code: `python3 scripts/publish.py publish post.json --approve <CODE>`. Optionally run `--dry-run` first to show the API calls.
6. Report the permalink. Then mark the calendar item: `python3 ../content-planner/scripts/planner.py status <id> published` (when the planner is installed).

## Decisions

- **Approval is per post and per version.** The code is a hash of type, caption, media and reel options. Any edit means a new check and a new approval. Never reuse a code from another post, never type a code the creator did not give, never approve "all of them" in one go unless the creator gives each code.
- **REVIEW posts** may be published only after you have stated each warning to the creator; BLOCKED posts cannot be published at all.
- **No token:** stop and walk through `references/setup.md`. Never ask for the Instagram password, a 2FA code or a session cookie; if offered, refuse and explain the token route.
- **Scheduling:** this tool publishes now. For a future time, use Meta Business Suite's scheduler or publish at the time with the creator present. Never leave a background job that posts later.
- **Quota:** the tool reads the live limit (Meta's pages say 50 or 100 per 24 h; `publisher.json` marks it `verify`). If it is used up, stop.

## Output format

```
PUBLISH PREVIEW  carousel  (4 media items)
   1. image https://.../slide_01.jpg ...
+-- caption, exactly as it will be posted --+
VERDICT: READY
APPROVAL CODE: 9F2C-41AB-07DE
```
After publishing:
```
PUBLISHED  media id 1789...
  https://www.instagram.com/p/...
Logged to ~/.creator-content-kit/publish-log.json
```

## Quality checklist

- [ ] Caption is the approved, gated version; no placeholders; claims are verified facts.
- [ ] Every media URL is public HTTPS; images are JPEG; carousel has 2-20 items.
- [ ] The creator saw the full preview and replied with this post's approval code.
- [ ] Published once (the log refuses duplicates); permalink reported; calendar updated.
- [ ] Token never printed, pasted into files in the repo, or committed.

## Errors and edge cases

- `REFUSED: approval code does not match`: the post changed after approval. Run check again and get a new approval.
- `API ERROR ... (code 190)`: token invalid or expired. Generate a new one (setup guide step 5).
- Container `ERROR`/`EXPIRED`: usually the media URL is not reachable or not a supported file. Open the URL in a private browser window; re-export as JPEG/MP4.
- Container still `IN_PROGRESS` after ~5 minutes (long videos): nothing was published; run the same publish command again later.
- `config_issue` in the result: the post is live but something (e.g. the caption) did not attach. Check the post in the app and fix it there.
- Account not professional, or not connected the right way: the token step fails; see the setup guide's requirements.

## Examples

`examples/post-image.json` + `examples/caption.txt`: READY, approval code printed, caption gate READY.
`examples/post-carousel.json`: 3 JPEG slides + 1 MP4, READY.
`examples/post-bad.json`: BLOCKED. A local SVG path, a PNG, a localhost URL, an unfilled `{{placeholder}}` and an unverified "40%" claim; no approval code is issued.
Wrong approval code, or a second publish of the same post: refused with exit 2 (see `examples/cases.json`).

## References

- `references/setup.md`: create the Meta app, connect the professional account, get a token, host media.
- `publisher.json`: API host and version, limits, polling, with confidence levels and Meta's doc URLs.
