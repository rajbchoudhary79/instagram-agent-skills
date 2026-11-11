---
name: content-humanizer
description: >-
  Make drafts read like the creator wrote them: remove invisible characters
  and clause dashes mechanically, flag AI-sounding vocabulary, template
  constructions, hedges, monotone rhythm and repetition with line numbers and
  plain-language fixes, rewrite in the creator's voice, and produce a quality
  report with a voice-preservation check. Use when the user says "humanize
  this", "make it sound less like AI", "make it sound like me", "clean this
  up", "too robotic", or before any caption, script or DM is finalised.
---

# content-humanizer

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

**What this is not:** an AI-detector bypass. The checks are local heuristics
for better writing. No score here guarantees how any detector or reader will
classify the text, and you never claim otherwise.

## When to use

- Every writing skill calls it before the gate.
- The user pastes text that reads generic, robotic or "AI".
- The user wants text rewritten in their own voice.

## Inputs

### Required
- The draft text.

### Optional
- The original (pre-edit) version, for the voice-preservation check.
- What it is (caption, script, DM, comment) and how much freedom to take (light polish vs rewrite).

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: voice samples, tone, words used / never used, emoji policy, `voice.md` if present. The samples are the target; read them before rewriting.
2. **Mechanical clean.** `python3 scripts/rewrite_check.py clean draft.txt --out clean.txt` removes invisible/format characters, swaps no-break spaces, rewrites clause dashes (`--dashes keep` to leave them), tidies whitespace. It never changes words.
3. **Diagnose.** `python3 scripts/rewrite_check.py report clean.txt`: human-writing score with reasons, then every finding with line, kind (slop, template, hedge, dash, triad, openers, banned, invisible) and a suggestion.
4. **Rewrite by hand.** Fix the findings in the creator's voice (`references/rewrite-guide.md`):
   - swap slop for the plain word or the concrete thing; often delete the sentence;
   - state points instead of "not X, but Y" or "here's the thing";
   - commit or cut hedges;
   - vary rhythm: one very short sentence, one longer one;
   - use the creator's own words from `words_i_use` and their samples;
   - keep meaning, facts and placeholders exactly.
5. **Verify.** `python3 scripts/rewrite_check.py report rewrite.txt --original draft.txt`: score again plus the voice check (content words kept, length change, own phrases lost, slop added). Fix any drift.
6. **Deliver.** The rewrite, the before/after score, a 3-5 line change summary, and the disclaimer line.

## Decisions

- **Light polish vs rewrite:** if the score is ≥ 75 and the voice check is clean, polish (fix only flagged spans). Under 55, rewrite from the meaning, then check meaning against the original.
- **Dashes:** remove clause dashes by default; keep them if the creator's own samples use them.
- **Emoji:** follow `voice.emoji_policy`.
- **Short texts** (< 40 words): rhythm and diversity are not measurable; rely on vocabulary, templates and banned words, and say the score is partial.
- **Flag disagrees with the creator's voice** (they really say "game-changer"): keep it, note it, and suggest adding it to `words_i_use`.

## Output format

```
HUMANIZED  (<type>)

<rewritten text>

SCORE  <before> -> <after>  (human writing quality; heuristic)
CHANGES
- removed 2 invisible characters, 3 clause dashes
- "unlock your potential" -> "bake on a weeknight"
- cut 2 hedges; split one 38-word sentence
VOICE CHECK  kept 0.82 of content words, 112 -> 96 words, no own phrases lost
Heuristic report. It does not call or emulate any AI detector; no score guarantees how text will be classified.
```

## Quality checklist

- [ ] Profile voice samples read before rewriting.
- [ ] Mechanical clean run; invisible characters gone.
- [ ] Every finding fixed or consciously kept (with a reason).
- [ ] Meaning, facts, numbers and {{placeholders}} unchanged.
- [ ] Voice check run against the original; no drift.
- [ ] No claim of detector-proof or "undetectable" text.

## Errors and edge cases

- Text in another language: invisible-character cleaning works; vocabulary checks are English-centric, so rely on reading and say so.
- Code, URLs or handles in the text: clean leaves them; check the dash rewrite did not touch ranges like `2020-2024` (it converts en dashes between digits to hyphens).
- The user asks to "make it undetectable": explain the limit in one line, then improve the writing anyway.
- Quotes from other people: never rewrite a quotation; flag it instead.

## Examples

Before (`examples/before.txt`):
`In today's fast-paced world, it's important to note that sourdough is not just bread — it's a lifestyle. Let's dive in and unlock your potential.`
report: 45 WEAK (capped: heavy slop), findings: 7 slop, 1 template, 1 dash, 1 hedge, 1 invisible
character, 1 banned word ("hustle", from the example profile).

After (`examples/after.txt`):
`Your starter tells you when it is ready. Feed it in the morning, and bake when it has doubled.`
report: 100 STRONG (partial: rhythm needs 3+ sentences). The voice check flags the length change and low
word overlap. That is expected for a full rewrite, so confirm the meaning by reading both.

## References

- `references/rewrite-guide.md`: patterns and replacements, rhythm, voice matching.
- `replacements.json`: suggestion table used by the report.
- Word lists: `../creator-core/config/lexicon.json`.
