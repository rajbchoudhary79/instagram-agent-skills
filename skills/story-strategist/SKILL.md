---
name: story-strategist
description: >-
  Plan and script Instagram Stories: the daily frame-by-frame sequence, which
  interactive sticker (poll, quiz, question, slider, add-yours, link,
  countdown) does which job, engagement strategy, and story-to-DM conversion
  funnels, with scripts and visual instructions per frame. Use when the user
  says "stories for today", "story sequence", "what should I post on stories",
  "story funnel", "poll ideas", "launch stories", or wants to warm up an
  audience before an offer.
---

# story-strategist

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- Daily stories, a launch sequence, a reel-promotion sequence, a behind-the-scenes day.
- Turning story viewers into conversations (DMs) or clicks, within the rules.

## Inputs

### Required
- The goal for today's sequence (one of: connect, teach, promote a post, collect questions, convert).

### Optional
- What happened today / what the creator can film (setting, props, time).
- Today's feed post (to promote), a launch date, the offer and link.
- Frames per day (default: profile `content.stories_per_day`, else 4-7).

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: voice, offer, CTA keyword and delivery, face on camera, disclaimers.
2. **Pick a sequence pattern** from `references/sequences.md` that fits the goal.
3. **Frames.** For each frame set: purpose (hook, context, value, interact, proof, convert, close), type (video/photo/text), what to say (script), on-screen text (≤ 20 words), visual, and at most one interactive sticker. `python3 scripts/story.py --stickers` lists what each sticker is for.
4. **Funnel order.** Get a tap before the ask: interaction (poll/quiz/slider/question) comes before any convert frame. Keep asks under ~30% of frames. One link per sequence.
5. **Conversion route.** Prefer "DM me WORD" or a question sticker that leads to a personal reply; automated replies only via Instagram's own tools/approved partners and only to people who replied (see dm-assistant). Link sticker for traffic, with clear link text.
6. **Write the JSON** (format in `scripts/story.py --help`) and run `python3 scripts/story.py seq.json --md storyboard.md`. Fix every FAIL/WARN.
7. **Humanize and gate.** content-humanizer on the scripts; `python3 scripts/core.py gate scripts.txt --type story`.
8. **Follow-up plan.** Say what to do with the sticker responses (share results tomorrow, reply to question answers, turn top questions into a reel via reel-creator).

## Decisions

- **Which sticker:** poll for a quick opinion; quiz to teach; slider for feeling; question to collect objections and DM openers; add-yours for reach; link to send traffic; countdown only for real dates.
- **Face vs text frames:** face frames build connection; use at least one if `visual.face_on_camera` is true.
- **Selling days:** even on launch days, lead with value and interaction. Countdown and link come after.
- **Proof frames:** verified facts or real screenshots with permission and private details removed.

## Output format

```
STORIES <date>  ·  goal: <goal>  ·  <n> frames

| # | purpose | type | say | on screen | sticker | visual |
| 1 | hook | video | "..." | ... | - | selfie at desk |
| 2 | interact | text | | ... | poll: "..." [A / B] | brand bg |
...

AFTERWARDS: <what to do with responses, tomorrow's follow-up>
CHECKS: story.py <verdict> · gate <verdict>
```

## Quality checklist

- [ ] Frame 1 is a hook or context, never an ask.
- [ ] One interactive sticker per frame, options within limits.
- [ ] Interaction before conversion; asks ≤ ~30% of frames; one link max.
- [ ] Every link sticker has a destination and descriptive text.
- [ ] On-screen text ≤ 20 words per frame.
- [ ] No fake urgency, fake scarcity or unverified results.
- [ ] story.py and gate run; responses have a follow-up plan.

## Errors and edge cases

- `FAIL options`: a poll/quiz with the wrong number of options. Fix to 2-4.
- `FAIL link`: link sticker without a URL. Add it or drop the sticker.
- `WARN funnel`: ask before interaction. Move the ask later or add a poll before it.
- Creator cannot film today: text and photo frames only; keep one personal line.
- Countdown for something with no date: replace with a question sticker.

## Examples

`examples/good-sequence.json`: hook → poll → value → quiz → "DM me STARTER" → question box. READY.
`examples/bad-sequence.json`: opens with a link ask, a 1-option poll, two interactive stickers on one frame,
2 of 3 frames selling → BLOCKED.

## References

- `references/sequences.md`: eight sequence patterns with frame plans.
- `stickers.json`: sticker jobs and rules (read by story.py).
