---
name: content-planner
description: >-
  Build and maintain the Instagram content calendar: weekly and monthly plans
  with formats, topics and publishing dates, a balanced mix of educational,
  entertaining, community and promotional posts across the creator's pillars,
  an idea backlog, and publishing status tracking from slot to published. Use
  when the user says "plan my week", "content calendar", "what should I post",
  "monthly plan", "add this idea", "mark it posted", or "is my content mix
  balanced".
---

# content-planner

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- Planning a week or month, filling open slots, or rebalancing the mix.
- Capturing ideas, tracking what is drafted / approved / published.
- After performance-auditor, to turn findings into next week's plan.

## Inputs

### Required
- A start date (week) or a month.

### Optional
- Posts per week, posting days and times (default: profile `content`).
- Pillars and mix targets (default: profile; fallback `mix.json`).
- Ideas, launches or dates to plan around (holidays, launches, events).
- Audit findings from performance-auditor.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: pillars + shares, mix, posts per week, days, times, formats, goal, offer.
2. **Slots.** `python3 scripts/planner.py plan --start <YYYY-MM-DD> --weeks 1` (or `--month YYYY-MM`). Slots get a date, time, format, pillar and type by weighted round-robin, so the mix hits the targets without clumping.
3. **Fill slots.** For each slot, propose a topic and a working hook that fit its pillar and type. Pull from the idea backlog first (`planner.py idea list`, then `idea use <idea> <slot>`), then from audit findings and the audience's pains. `planner.py assign <id> --topic "..." --hook "..."`.
4. **Launches and dates.** Place promotional slots in the run-up to real launches only; keep promotional ≤ the mix target outside launch weeks.
5. **Check balance.** `python3 scripts/planner.py balance`. Rebalance anything ±15 points off target, or explain why (e.g. launch week).
6. **Show the plan.** `planner.py export --md week.md` and present it. Offer to hand slots to reel-creator / carousel-creator / story-strategist.
7. **Track.** As work moves: `planner.py status <id> drafted|approved|scheduled|published|skipped`. Set `approved` and later only when the creator says so.

## Decisions

- **Type definitions** (`mix.json > type_definitions`): educational teaches one usable thing; entertaining builds liking; community starts conversation; promotional sells (verified proof only).
- **Format choice:** follow the slot unless the topic clearly fits another format (lists and frameworks → carousel; stories and demos → reel). Change it with `assign --format`.
- **Capacity:** plan what the creator can sustain. If they missed last week's slots, plan fewer, not more.
- **Audit-driven changes:** only shift the plan on patterns with 3+ posts per group from performance-auditor; otherwise call it a test.
- **Monthly plans:** fill the first week in detail, later weeks with pillar + type + a topic direction.

## Output format

```
WEEK OF <date>  ·  <n> posts  ·  mix: edu <a>% ent <b>% com <c>% promo <d>% (targets ...)

| date | day | time | format | pillar | type | topic | working hook | status |
...

BACKLOG: <n> ideas (top 3 listed)
NEXT: which slots go to reel-creator / carousel-creator first
```
The calendar file path is printed by `planner.py list`.

## Quality checklist

- [ ] Profile pillars, mix, cadence and days used (or fallback stated).
- [ ] Every slot has a format, pillar and type; filled slots have a topic and working hook.
- [ ] Balance checked; deviations explained.
- [ ] Promotional content only for real offers and launches.
- [ ] Status changes past `drafted` only on the creator's word.
- [ ] Plan stored in the calendar file, not only in chat.

## Errors and edge cases

- Dates already planned: `plan` skips them; `--replace` replaces empty slots only; `--allow-double` adds a second post that day.
- No pillars in the profile: slots get "(no pillars set)"; ask for 2-4 pillars before filling.
- Unknown status: planner.py lists the valid ones.
- Wrong date format: use ISO `YYYY-MM-DD`.
- Several calendars (e.g. two brands): use `--file path/to/calendar.json`.

## Examples

```
planner.py plan --start 2026-11-16 --weeks 2
c-0001  2026-11-16 Mon 08:30  reel      Starter care    educational  slot
c-0002  2026-11-17 Tue 18:00  carousel  Bake schedules  entertaining slot
c-0003  2026-11-19 Thu 08:30  reel      Kitchen life    community    slot
...
balance -> Starter care 38% (target 40), Bake schedules 38% (35), Kitchen life 25% (25)
```
Good: every slot filled with a topic tied to a pillar and an audience pain; promotional slot next to the checklist giveaway.
Bad: seven reels all "sourdough tips", no community post, a "promo" slot for an offer that does not exist.

## References

- `references/planning.md`: pillar design, weekly rhythm, monthly themes, status lifecycle.
- `mix.json`: fallback mix, formats and type definitions.
