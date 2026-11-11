---
name: creator-core
description: >-
  Shared foundation for the Instagram skills. Sets up and reads the creator
  profile every skill depends on, scores any draft against the JSON rubrics,
  runs the final quality gate before anything goes to the creator for approval,
  and runs multi-skill workflows (topic to finished reel, long video to a week
  of posts). Use when the user says "set up my Instagram profile", "write my
  voice file", "final check", "score this", "is this ready to post", or asks
  for an end-to-end pipeline across several Instagram skills.
---

# creator-core

The other twelve skills are specialists. This one holds what they share: the
creator profile, the scoring engine, the gate, and the pipelines that chain
them. All paths below are relative to this skill's folder.

## When to use

- First run, or the user asks to set up / update their creator profile or voice.
- Any draft needs a final check before the creator sees it as "ready".
- The user wants a score or a comparison of drafts on a rubric.
- A request spans several skills ("research my niche, then write three reels and captions").

Do not use it to write content. Route writing to the specialist skill.

## Inputs

### Required
- For setup: answers to the profile interview (or 3-5 real samples of the creator's writing).
- For gate / score: the draft text and its type (caption, reel, carousel, story, comment, reply, dm, bio).

### Optional
- `--keywords` search phrases; `--post` the post being replied to; `--refs` inspiration texts (originality).
- A specific profile path (`--profile`), otherwise auto-discovered.

## Workflow

### A. Set up the creator profile
1. `python3 scripts/profile.py where` to see where it will live.
2. `python3 scripts/profile.py init` creates `profile.json` plus `voice.md`, `brand.md`, `audience.md`, `content-strategy.md`.
3. Interview the creator using `references/profile-interview.md`. Ask in small batches (3-4 questions), not a form dump. Prefer their real samples over adjectives.
4. Write answers into `profile.json`. Put every number, client, result or credential they confirm into `verified_facts` with a source. Never fill a field with a guess; leave it empty.
5. `python3 scripts/profile.py check` and fix schema errors. Report completeness and the most useful missing fields.

### B. Read the profile (every skill does this first)
`python3 scripts/profile.py show` prints the brief. Exit code 3 means there is no profile: ask for niche, audience, tone and language in one message, label the answers as session assumptions, and offer to save them.

### C. Score a draft
`python3 scripts/score.py --rubric <name> draft.txt` (`--list` for rubrics; `--split lines|blocks` to rank options). Report the score, the band, the weakest criterion and its fix, and the limitation that matters for this draft.

### D. Final gate (before any "ready" handoff)
`python3 scripts/gate.py draft.txt --type <type>` then act on the verdict:
- **BLOCKED**: fix and re-run. Never present a blocked draft as final.
- **REVIEW**: present it with each warning stated plainly (e.g. "fill {{amount}}").
- **READY**: present it. Still the creator's decision; nothing is posted.

### E. Pipelines
Run the specialist skills in the order given in `references/workflows.md`. Between steps, pass a handoff packet (`scripts/handoff.py new ...`, validated with `handoff.py validate`) so verified facts and assumptions stay separate. Skip any step whose output already exists.

## Decisions

- **Which rubric?** hook (first lines), caption, storytelling (scripts, carousels), engagement (compare drafts of one post), originality (vs inspiration), human (any text), comment, dm, bio.
- **Which gate type?** Match what will be published. For a reel, gate the script; gate the caption separately as `caption`.
- **A number appears that is not in verified_facts.** Ask the creator. True: add it to `verified_facts` with a source. Unknown: replace with `{{placeholder}}`.
- **Score vs judgment conflict.** Scores are heuristics. If a draft scores low for a reason that does not apply (e.g. a deliberate one-word hook), say so and keep it.
- **Pipeline length.** Use the shortest chain that answers the request. One reel needs reel-creator, caption-writer, content-humanizer and the gate, not research.

## Output format

Setup: a short summary of what was saved, completeness %, and the 3 most valuable missing fields.
Score: `<rubric> <score> <band>`, weakest criterion with its fix, one-line limitation.
Gate: the verdict line, every FAIL/WARN as a bullet, then the draft. End with: "Nothing has been posted."

## Quality checklist

- [ ] Profile read before any writing; missing profile handled with labelled assumptions.
- [ ] No invented facts entered into `verified_facts`; every entry has a source.
- [ ] Scores reported with what they measure and their limits, never as reach predictions.
- [ ] Gate run on everything presented as final; verdict and warnings shown.
- [ ] Handoffs keep `verified` and `assumptions` separate.
- [ ] No publishing, scheduling or account changes without explicit approval.

## Errors and edge cases

- `profile.py` exit 3: no profile. Ask the minimum four questions; do not block the task.
- Schema errors: show them, fix with the creator, re-run `check`.
- `creator-core not found` from another skill: creator-core must sit next to it in the same `skills/` folder, or set `IG_CORE_DIR`.
- A rubric file fails to load: `score.py` prints the problem (unknown feature, missing `why`). Fix the JSON.
- Non-English profile: scores lean on English word lists. Say the vocabulary checks are weaker and rely more on judgment.

## Examples

Good gate handoff:
```
QUALITY GATE  type=caption
  WARN  1 placeholder(s) to fill before posting: {{amount}}
  PASS  Caption quality 88 (threshold 70)
VERDICT: REVIEW
```
"Ready apart from one thing: fill `{{amount}}` with the real figure, or I'll cut that line."

Bad: presenting a BLOCKED draft as final, or saying "this will go viral (score 92)".

See `examples/` for a sample handoff packet.

## References

- `references/profile-interview.md`: the interview, in order, with what each answer feeds.
- `references/workflows.md`: pipelines, handoff rules, when to skip steps.
- `references/scoring.md`: rubric format, every feature, how to add or tune a rubric.
- `references/safety.md`: platform rules and what this system will not do.
