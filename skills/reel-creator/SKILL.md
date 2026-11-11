---
name: reel-creator
description: >-
  Turn an idea into a shootable Instagram Reel: idea angles, several hooks
  scored against a 24-formula library, the spoken script, scene-by-scene
  breakdown with on-screen text, visuals, transitions and edit notes, a timed
  beat sheet with duration estimate, and CTA options, in the creator's voice.
  Use when the user says "write a reel", "script this", "reel idea", "give me
  hooks", "how long is this reel", or hands over a topic, a story or a research-log
  entry to film.
---

# reel-creator

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- A topic, story, opinion or research-log entry needs to become a reel.
- The user wants hooks, wants hooks ranked, or wants a script timed.
- content-repurposer or viral-researcher hands over a moment or a formula.

Not for: captions (caption-writer), carousels (carousel-creator), stories (story-strategist).

## Inputs

### Required
- The idea: a topic, a claim, a story, or a transcript excerpt.

### Optional
- Target length in seconds (default: 20-35 s for teaching, 7-15 s for a single punchline).
- Format: talking head, voiceover + b-roll, POV skit, screen recording, tutorial, green screen.
- Research-log entries or formula ids from viral-researcher; source timestamps from content-repurposer.
- The CTA goal (comment keyword, save, follow, DM) if it differs from the profile.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`. Note pace (wpm), tone, words used/never used, CTA keyword, visual style, verified facts. No profile: ask niche, audience, tone, language in one message and label them as assumptions.
2. **Angle.** If the idea is broad, offer 3 angles (each: the claim, who it is for, why now) and let the user pick, or pick the one most specific to the audience's pains and say why.
3. **Hooks.** Write 5 hooks from at least 3 formula families (`python3 scripts/hook_rank.py --formulas`). Spoken hook ≤ ~3 s. Put them one per line in a file and run `python3 scripts/hook_rank.py hooks.txt`. Rewrite anything under 65 or with a dealbreaker, re-score, and keep the top 3.
4. **Structure.** Choose a structure from `references/script-structures.md` that fits the angle (myth-fix, mistake-fix, story, list, tutorial, POV, before/after).
5. **Script.** Write in the creator's voice using the beat format below. One idea per beat. Something concrete every 2-3 beats (a number, an object, an on-screen visual). Facts only from the profile or the user; otherwise `{{placeholder}}`.
6. **Scenes and edit.** For each beat add on-screen text, the visual and the edit/transition (`references/editing.md`). On-screen text is short enough to read while the line is spoken.
7. **Time it.** `python3 scripts/script_timer.py script.txt --target <seconds>`. Fix every WARN: long hook, long static beats, unreadable text, abstract runs, off-target length.
8. **CTA.** Offer 3 CTA lines tied to the goal (keyword, save, share, follow); recommend one. One ask per reel.
9. **Humanize and gate.** Run content-humanizer on the script, then `python3 scripts/core.py gate script.txt --type reel`. Act on the verdict.
10. **Hand off.** Offer caption-writer (job A: the video carries the hook). Nothing is posted.

## Decisions

- **Hook choice:** highest score unless it promises something the script does not deliver. Delivery beats score.
- **Proof formulas** (price_of_error, from_to, experiment, show_artifact) need a verified fact. No fact → choose another formula or use a placeholder and flag it.
- **Length:** cut until every beat earns its place. If the beat sheet runs >15% over target, cut a beat, do not speed-read.
- **Loop:** if the last line can echo the hook, use it. Otherwise end on the CTA.
- **Talking head vs b-roll:** follow `visual.face_on_camera`. Without a face, every beat needs a visual.
- **Trending audio:** suggest a type ("low, steady instrumental under voice"), never claim a specific track is trending.

## Output format

```
REEL: <working title>  ·  <format>  ·  target <n>s  ·  est. <n>s at <wpm> wpm

HOOKS (scored)
1. <hook>  <score> <band>  formula: <id>    <- recommended
2. ...
3. ...

SCRIPT / SCENES
| # | time | spoken | on-screen text | visual | edit |
| 1 | 0:00-0:03 | ... | ... | ... | ... |

CTA OPTIONS
- <cta 1>  (recommended)
- <cta 2>
- <cta 3>

FILMING NOTES: <setting, framing, props, b-roll list>
CHECKS: script_timer.py <flags or "clean">, gate <verdict>, placeholders <list or none>
```
Also save the script in beat format (below) so it can be re-timed.

Beat format:
```
HOOK: <spoken line> [text: on-screen] [visual: shot] [cut]
<spoken line> [visual: ...] [zoom]
CTA: <spoken line> [text: Comment WORD]
```

## Quality checklist

- [ ] Profile read; voice and banned words respected.
- [ ] 5 hooks written, scored, top 3 shown with scores and formula ids.
- [ ] Hook ≤ ~3 s spoken, with on-screen text.
- [ ] Every beat has a visual or an edit; nothing static for more than ~6 s.
- [ ] Something concrete at least every 3 beats.
- [ ] script_timer.py run; every WARN fixed or explained.
- [ ] One CTA, matched to the goal.
- [ ] No invented numbers, clients or stories; placeholders flagged.
- [ ] content-humanizer and the gate run; verdict shown.

## Errors and edge cases

- Idea too vague ("content about mindset"): ask one question (who, and what changes for them), or offer 3 specific angles.
- User supplies a story with numbers: ask whether they can be stated publicly; add to `verified_facts` only on yes.
- Script far over target: show which beats to cut, ranked by how little they add.
- Non-English: hook scoring leans on English word lists; rely more on the formula match and judgment, and say so.
- Sensitive niche (health, finance, legal): add the profile's disclaimers; avoid outcome promises.

## Examples

Good hook set (scored with the example profile):
```
-> 85.1 STRONG  Strict feeding times are wrong for home bakers.            wrong_default   3.2s
   78.9 OK      How to bake sourdough without a free weekend.              how_to_without  3.2s
   78.9 OK      Nobody warns home bakers that the fridge does the work.    hard_way        3.9s
```
Bad: `Hi everyone, so in this video we're going to chat about sourdough` (25, greeting dealbreaker);
`Stop scrolling if you want to unlock your potential 🔥` (45, attention-begging + slop).

`examples/good-script.txt` times cleanly at ~26 s against a 30 s target; `examples/bad-script.txt`
gets an 11.8 s hook, static beats and an abstract run. Run `script_timer.py` on both to see.

## References

- `references/script-structures.md`: seven structures with beat templates.
- `references/editing.md`: transitions, b-roll, on-screen text, safe zones, filming checklist.
- Hook library: `../creator-core/config/hook_formulas.json` (`hook_rank.py --formulas`, `--formula <id>`).
