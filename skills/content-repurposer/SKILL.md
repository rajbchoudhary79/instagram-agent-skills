---
name: content-repurposer
description: >-
  Turn long content into Instagram posts without changing what the creator
  said: find the clip-worthy moments in a YouTube video, podcast, livestream,
  webinar or article transcript, map them to reels and carousels, and write
  each piece so it stands alone while staying faithful to the source, with
  timestamps for every claim. Use when the user says "repurpose this",
  "turn my video/podcast/article into reels", "clips from this episode",
  "make carousels from this blog post", or shares a transcript, SRT or VTT file.
---

# content-repurposer

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- The creator has long-form content (their own) and wants short-form from it.
- A week's content should come from one source (Pipeline 2 in `../creator-core/references/workflows.md`).

Only repurpose content the creator owns or has rights to. For someone else's content, use viral-researcher to learn the pattern instead.

## Inputs

### Required
- The source as text: SRT/VTT captions (best: real timestamps), a transcript, or the article text. YouTube auto-captions exported by the creator are fine.

### Optional
- How many pieces and which formats; the week to slot them into.
- The source's title, URL and date (for "full episode" CTAs).
- Moments the creator already likes.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: voice, pillars, CTA, formats.
2. **Shortlist.** `python3 scripts/segment.py source.srt --top 8` (use `--window 30` for punchier clips, 60 for stories). Each moment comes with timestamps, a candidate hook sentence, component scores and a suggested format.
3. **Read the passages** around each shortlisted moment in full (one window before and after). Drop moments that depend on context the clip will not have. Keep 3-5 for a week.
4. **Map to formats** (`references/format-mapping.md`): stories and opinions → reel; lists, steps, frameworks → carousel; strong single lines → quote reel or text post; Q&A → story question sticker follow-up.
5. **Write each piece** with the specialist skill (reel-creator / carousel-creator / caption-writer). Keep the speaker's claims, numbers and meaning exactly; tighten wording, never add claims. Each piece stands alone: no "as I said earlier".
6. **Fidelity note.** For every piece, list the source timestamps and the original sentences it relies on. Paraphrases must not change the meaning; quotes must be verbatim.
7. **Plan.** Hand the pieces to content-planner as drafted items with the source noted. Gate each piece.

## Decisions

- **Clip vs re-record:** if the source moment is strong on camera and under ~60 s, suggest clipping it (with timestamps for the editor); otherwise script a fresh reel from it.
- **Numbers in the source:** the speaker said them, so they can be used with the same wording; they still go through the gate (add to verified facts with the source timestamp if the creator confirms).
- **Weak opening, strong middle:** hooks can come from anywhere in the passage, as long as the clip delivers on them.
- **Articles:** no timestamps; segment.py estimates positions (marked ~). Use paragraph references instead.

## Output format

```
SOURCE: <title> (<length>)  ·  <n> moments shortlisted, <k> used

| # | source time | moment | format | hook | pillar |
| 1 | 0:46-1:10 | morning-feed method | carousel | "Stop feeding at midnight." | Starter care |
...

PIECE 1 (carousel): <full draft or handoff to carousel-creator>
  FIDELITY: 0:46 "That's when I stopped feeding at midnight." 0:58 "Step one, feed it in the morning..."
...
CALENDAR: added as drafted items c-00xx ...
```

## Quality checklist

- [ ] The creator owns the source (or has rights to it).
- [ ] Every piece lists source timestamps and original sentences.
- [ ] No added claims, numbers or examples beyond the source and profile.
- [ ] Each piece stands alone without the original's context.
- [ ] Formats chosen by content shape, not by habit.
- [ ] Pieces gated and slotted into the plan.

## Errors and edge cases

- Auto-captions with errors: fix obvious transcription mistakes; flag anything uncertain ("{{check: 'rye' or 'dry'?}}").
- Very long sources (2 h+): run segment.py with `--top 15`, then read in order of score.
- Multiple speakers: attribute lines correctly; do not put a guest's words in the creator's mouth. Guest quotes need the guest's OK.
- No strong moments: say so and suggest one fresh reel on the episode's main idea instead of forcing weak clips.

## Examples

`examples/episode.srt` (1:22, `--window 20 --top 3`):
```
1. 0:46-1:10  score 82  -> reel    hook: "If you want to try it, here's how."   (steps: carousel-able too)
2. 0:24-0:46  score 54             hook: "Here's the thing nobody warns new bakers about."
3. 1:10-1:22  score 25             outro: skip
```
Good use: moment 1 → a 3-step carousel; moment 2 → a reel built on "A starter that looks dead is usually just hungry", with the 2019 story (0:34) as proof because the speaker said it.
Bad use: a reel claiming "this doubled my rise", which the source never says.

## References

- `references/format-mapping.md`: which source shapes become which formats, and the fidelity rules.
