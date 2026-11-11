---
name: performance-auditor
description: >-
  Post-mortem on the creator's published Instagram content from their own
  Insights or Meta Business Suite export: rates per reach (saves, shares,
  comments, follows), engagement, watch ratio and outlier multiples where the
  data has them, patterns by format, pillar, hook formula and weekday, top and
  bottom posts, and specific recommendations, never inventing missing
  analytics. Use when the user says "audit my content", "what's working on my
  account", "why did this post flop", "analyse my insights", or shares a
  posts export or screenshot of their metrics.
---

# performance-auditor

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- Weekly / monthly review, before planning the next cycle (content-planner).
- One post over- or under-performed and the creator wants to know why.

Not for: other people's accounts (viral-researcher).

## Inputs

### Required
- The creator's own post data: a CSV export (Meta Business Suite / Insights) or a table they type from screenshots. At least reach or views per post.

### Optional
- Pillar per post (or let the audit infer it from topics and confirm).
- Average watch time and duration (for watch ratio), follows, profile visits.
- The period's goal (from the profile) to choose the headline metric.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: goal, KPIs, pillars, formats.
2. **Data.** Put the export in CSV (recognised columns in `scripts/audit.py --help`). Copy numbers exactly. Screenshots: transcribe only what is visible.
3. **Run.** `python3 scripts/audit.py posts.csv` (it picks a headline metric; override with `--rank-by saves_per_reach` etc. to match the goal: leads → follows/shares, authority → saves, reach → multiple).
4. **Coverage first.** Report which metrics exist and which are missing. Missing metrics are never estimated or implied ("retention: not in the data").
5. **Read the top and bottom posts.** Look at each one's hook, format, topic, length and CTA. Tie differences to the observable features; label explanations as hypotheses.
6. **Patterns.** Use the group tables. Only state a pattern with 3+ posts per group and a ≥1.3x gap; smaller differences are "worth testing".
7. **Recommendations.** 3-5, each: what to do, the evidence (metric, groups, n), and how to test it next week (one variable at a time). Hand off to content-planner.

## Decisions

- **Headline metric:** follow the goal. Shares and saves per reach are usually more informative than views; views alone measure distribution.
- **Denominator:** reach when present; otherwise views, with the caveat stated.
- **Small accounts / few posts:** under ~10 posts, describe; do not generalise.
- **Outliers:** one huge post skews averages; the tables use medians for that reason.
- **Causation:** never claim a format "causes" results. Say "in this data, X had a higher median Y (n=...)".

## Output format

```
AUDIT <period>  ·  <n> posts  ·  rates per reach  ·  headline: saves per reach

COVERAGE  reach 16 · saves 16 · shares 16 · views 10 · watch time: not in data
TOP 3 / BOTTOM 3   (metric, format, pillar, formula, hook)
PATTERNS
- Carousels: median saves/reach 2.64% vs reels 0.85% (n=6 vs 10)
- Starter care pillar: 2.64% vs Kitchen life 0.83% (n=6 vs 5)
- Formula differences: too few posts per formula to conclude (except numbered_list n=4 vs confession n=5)
RECOMMENDATIONS
1. <action>. Evidence: <...>. Test: <...>.
DATA NOTES  exported <date> by the creator; no metrics estimated
```

## Quality checklist

- [ ] Only the creator's own data; numbers copied exactly.
- [ ] Coverage and missing metrics stated up front.
- [ ] Patterns need n ≥ 3 per group and a ≥ 1.3x gap; otherwise "test".
- [ ] Correlation language only; explanations labelled as hypotheses.
- [ ] Recommendations each have evidence and a test.
- [ ] Handoff to content-planner for next week.

## Errors and edge cases

- Column names not recognised: rename to the ones in `--help` (or tell the agent which column is which).
- Mixed date formats: ISO (YYYY-MM-DD) is safest; unknown formats leave the weekday blank.
- Only views: rates fall back to views and the report says so; saves/shares rates may be missing.
- Very recent posts: still accumulating; note posts under ~7 days old.
- Screenshot of a single post: analyse it alone against the profile's typical numbers only if the creator gives them.

## Examples

`examples/posts.csv` is **synthetic sample data** (16 posts) for trying the tool:
```
By format: carousel median saves/reach 2.64% vs reel 0.85% (n=6 vs 10)
By formula: numbered_list 2.64% vs confession 0.83% (n=4 vs 5); others too few
Missing entirely: impressions, profile_visits, avg_watch, duration -> "nothing here speaks to retention"
```
Good recommendation: "Next week, turn the two strongest reel topics into carousels and keep everything else the same; compare saves per reach."
Bad: "Reels are dead, post only carousels" (overreach), or quoting a retention rate that is not in the data.

## References

- `references/metrics.md`: what each metric means, which goal it serves, common misreads.
