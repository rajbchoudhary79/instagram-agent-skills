---
name: profile-auditor
description: >-
  Audit an Instagram profile out of 100 against a 10-part rubric (photo,
  username, name field, bio, CTA, link, highlights, pinned posts, content
  consistency, positioning), explain every lost point, list fixes in priority
  order, and rewrite the bio and name field. Use when the user says "audit my
  profile", "review my bio", "rewrite my bio", "why aren't people following",
  "optimize my Instagram profile", or shares a profile screenshot.
---

# profile-auditor

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- The creator wants a profile review, a bio rewrite, or to know why visits do not turn into follows.
- After a positioning change, or before a launch.

## Inputs

### Required
- A profile snapshot the creator provides: username, name field, bio, link(s), highlights, pinned posts. A screenshot is fine; you transcribe it.

### Optional
- The last 9-12 posts with format, topic and pillar (for consistency).
- A description or screenshot of the profile photo.
- Profile visits / follows numbers from Insights (only if the creator shares them).

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: positioning, audience, search terms, offer, CTA, pillars, verified facts.
2. **Snapshot.** Write the snapshot JSON (format in `scripts/profile_audit.py --help`). Copy text exactly, including emoji and line breaks. Never fetch the profile yourself.
3. **Auto-score.** `python3 scripts/profile_audit.py snapshot.json`.
4. **Manual criteria.** Judge the photo and positioning against `profile_rubric.json` full-marks lines; explain each deduction in one sentence. Re-run with `--manual '{"photo": n, "positioning": n}'` for the final score.
5. **Fix order.** Present fixes by points lost, biggest first. Each fix says what to change and why.
6. **Rewrite.** Write 3 bios (≤ 150 chars: who it's for, what they get, one verified proof point if available, one next step) and 2 name-field options containing the main search phrase. Score them: `python3 scripts/core.py score --rubric bio bios.txt --split blocks`. Gate the chosen bio: `core.py gate bio.txt --type bio`.
7. **Highlights and pinned plan.** Recommend 3-7 highlight titles (≤ 15 chars) and the three pinned posts' jobs, using existing content where possible.
8. **Apply.** The creator edits their own profile. Never ask for login details.

## Decisions

- **Name field vs bio:** the name field is searchable, so the search phrase goes there; the bio converts.
- **Proof in the bio:** only verified facts. No proof yet: lead with the specific outcome instead.
- **Link:** one destination that matches the bio's CTA. Multiple links only if the bio says which to tap.
- **Username changes:** recommend only when the current one is hard to say or spell; changing breaks old mentions and links. Say so.
- **Consistency under 80%:** the fix is usually a pillar decision, not more posting. Hand off to content-planner.

## Output format

```
PROFILE AUDIT @<handle>   <score>/100   (auto <n>/<86> + manual <n>/<14>)

| criterion | score | why |
| Bio clarity | 11.2/22 | doesn't say who it's for; no outcome; no next step |
...

FIX FIRST
1. <fix> (+<points>)
2. ...

BIO OPTIONS (scored)
1. <bio>   <score>  <chars>/150   <- recommended
2. ...
NAME FIELD: <option 1> | <option 2>
HIGHLIGHTS: <titles>     PINNED: <post 1 job>, <post 2 job>, <post 3 job>
```

## Quality checklist

- [ ] Snapshot transcribed exactly; nothing fetched or logged into.
- [ ] Every lost point explained; manual scores justified.
- [ ] Fixes ordered by points lost.
- [ ] Bios ≤ 150 characters, scored, gated; proof only from verified facts.
- [ ] Name field contains the search phrase.
- [ ] Username change advice notes its cost.

## Errors and edge cases

- Screenshot unreadable: ask for the text, or mark the field unknown (not scored).
- Fewer than 6 recent posts: consistency is "pending", not zero. Say so.
- No creator profile: search-term checks are weaker; ask for the 2-3 phrases their audience searches.
- Business vs creator account features (contact buttons, categories): mention only what the creator confirms they see.

## Examples

`examples/snapshot-before.json`: auto 27.7 of 86 (32%), weakest: bio (no audience, no outcome, no CTA), username with digits and two separators, no link, no pinned posts.
`examples/snapshot-after.json` with `--manual '{"photo": 9, "positioning": 3}'`: 94.7/100 (only the manual positioning point left).

Good bio: `Sourdough for home bakers with a 9-to-5. / Taught 220 students in 2025 workshops. / Get the free starter rescue checklist ↓` (bio rubric 85, 119/150, proof is a verified fact).
Bad bio: `Baker ✨ Plant mom 🌿 Dreamer 🌙 Living my best life | Portland` (bio rubric 51: no audience, no outcome, no next step).

## References

- `profile_rubric.json`: the 10 criteria, points, full-marks definitions.
- `references/bio-formulas.md`: bio structures and name-field patterns.
