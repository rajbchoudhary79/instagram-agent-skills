---
name: caption-writer
description: >-
  Write and check Instagram captions: an opening line built for the ~125
  characters the feed shows before "... more", the body with natural search
  phrases, specific hashtags within the current cap, and several CTA variations,
  with a feed preview and a linter for length, hashtags, links and asks. Use
  when the user says "write a caption", "caption this reel/carousel", "fix my
  caption", "hashtags for this", "how will this look in the feed", or has a
  post ready that needs text.
---

# caption-writer

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- A reel, carousel or photo needs its caption.
- An existing caption needs checking, shortening or hashtags.
- reel-creator / carousel-creator / content-repurposer hands over a finished piece.

## Inputs

### Required
- What the post is: the script, slide copy, or a description of the photo/video.

### Optional
- Search phrases (default: profile `audience.search_terms`).
- The CTA goal (default: profile `goals.cta`).
- A draft caption to fix. Character budget. Language.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: voice, emoji policy, CTA keyword and what it delivers, search terms, disclaimers.
2. **Decide the job.**
   - **Job A, the post carries the hook** (most reels): line one supports the video. It names the payoff or the ask plainly; it does not compete with the spoken hook.
   - **Job B, the caption is the hook** (photos, some carousels, text-light reels): line one is a hook; score it with `core.py score --rubric hook`.
   Say which job you chose.
3. **Line one.** Fits inside ~125 characters with margin, ends on a complete thought, no greeting, no hashtag or emoji first.
4. **Body.** 2-6 short paragraphs with blank lines between. Put 2-3 search phrases in naturally as words people type. Add value the post did not have room for (the step, the example, the nuance). Facts only from the profile or the user.
5. **CTA variations.** Write 3 (e.g. comment keyword / save / share-to-someone). Recommend one; the caption carries only that one.
6. **Hashtags.** 0 to the cap in `platform.json` (currently set to 5, confidence: verify), on the last line: specific topic labels, no generic tags (#fyp, #viral, #explore). Hashtags are labels, not a reach lever.
7. **Alt text** for photos and carousels: one plain sentence describing the image.
8. **Lint.** Save to a file and run `python3 scripts/caption_lint.py caption.txt` (add `--keywords` if not using the profile's). Fix every FAIL; decide each WARN out loud.
9. **Humanize and gate.** content-humanizer on the caption, then `python3 scripts/core.py gate caption.txt --type caption`.
10. **Deliver** the copy-ready block plus the receipt. If there is a link, say where it goes (bio, story link sticker, keyword DM), never in the caption.

## Decisions

- **Length:** match the job. A reel caption that supports the video is often 150-600 characters. A Job B photo caption can run long if every paragraph earns its place.
- **Keyword CTA:** one word, uppercase in the caption, no spaces, and spoken in the video too. Make sure the delivery exists (profile `goals.cta.keyword_delivers`). If it does not, use save or share.
- **Hashtag count:** fewer, specific ones. If the creator wants many, explain the cap and its confidence level, and stay within it.
- **Comparing variants:** put them in one file separated by `---` and run `caption_lint.py file --split blocks`.
- **Disclaimers:** if the profile lists required disclaimers, include them; the gate checks.

## Output format

```
CAPTION  (job A: the reel carries the hook)

<caption text, exactly as it should be pasted>

ALT TEXT: <one sentence>            (photos/carousels)
FIRST COMMENT: <only if needed>     (e.g. a link reference; never required)

CTA OPTIONS
- Comment STARTER and I'll send you the rescue checklist.   <- used
- Save this for the next time your starter stops rising.
- Send this to the friend who keeps throwing out their starter.

RECEIPT
visible: <n>/~125 chars before the cut · ask: one (<type>) · hashtags: <n>/<cap>
search phrases: "<a>" (para 2), "<b>" (para 3) · caption score <n> · gate <verdict>
```

## Quality checklist

- [ ] Job A or B chosen and stated.
- [ ] Line one fits the visible window and stands alone.
- [ ] Exactly one ask in the caption; 3 CTA options offered.
- [ ] Search phrases present as natural words.
- [ ] Hashtags within the cap, specific, last line.
- [ ] No link in the caption body.
- [ ] caption_lint.py: no FAIL; WARNs addressed.
- [ ] content-humanizer run; gate verdict shown; no unverified claims.

## Errors and edge cases

- caption_lint.py `FAIL hashtag_count`: cut to the cap; keep the most specific.
- `WARN keywords missing`: weave them in or say why not (e.g. a community post).
- `WARN link`: move the link; mention the bio or a DM keyword instead.
- Emoji box misalignment in the preview: cosmetic (emoji are double-width in terminals).
- Non-English caption: the preview and limits still apply; slop and ask detection are English-centric.
- Truncation varies by device: `--window 100` tests a tighter preview.

## Examples

Good (`examples/good-caption.txt`, scored with the example profile):
```
Stop throwing out your sourdough starter after one flat day.
...
Comment STARTER and I will send you the rescue checklist I use.
#sourdoughstarter #beginnersourdough
```
caption_lint.py: PASS length, first line 60/125, one ask, 2 hashtags, all three search phrases · caption quality 100, verdict READY.

Bad (`examples/bad-caption.txt`): opens "Hey guys! 🔥🔥", a dead link, three asks, seven hashtags incl. #viral #fyp → FAIL greeting, FAIL hashtag cap, verdict BLOCKED, caption quality 40.

## References

- `references/caption-patterns.md`: line-one patterns per job, body shapes, CTA wording by goal.
- Platform limits: `../creator-core/config/platform.json`.
