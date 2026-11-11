---
name: viral-researcher
description: >-
  Research what is working in a niche on Instagram right now and turn it into a
  reusable research log: collect observations the creator gathers (never scraped),
  rank posts by how far each beat its own account's baseline, classify the hook
  formula, format and topic, and extract patterns to adapt, never copy. Use when
  the user says "what's working in my niche", "find viral reels", "research
  competitors", "build a swipe file", "what hooks are working", or "trend
  research".
---

# viral-researcher

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- Before a content batch, to find angles and formulas that are working for peers.
- When the creator wants a research log or a pattern read on accounts they admire.
- When reel-creator needs a proven structure for a topic.

Not for: auditing the creator's own posts (performance-auditor).

## Inputs

### Required
- Niche, from the profile or the user.
- Observations: posts the creator collected (URL, account, format, hook, views and whatever else they can see), as CSV/JSON or pasted text you convert to CSV.

### Optional
- Account list to study (5-10 peers, slightly ahead of the creator).
- Account median views per account (from the creator's notes or a tool they use legitimately).
- Exported data from official sources (Graph API `business_discovery`, a Meta-approved analytics tool).
- Topic focus, time window.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show` for niche, audience, pillars, search terms.
2. **Plan the collection.** Give the creator a short brief (`references/research-method.md`): which 5-10 accounts, how many recent reels each (10-15), what to record. The creator browses in their own app; you never log in, crawl or automate.
3. **Normalise.** Put what they bring into the CSV columns in `scripts/research_log.py --help`. Copy numbers exactly; blank when unknown. Record `source` and the date for every row.
4. **Rank.** `python3 scripts/research_log.py observations.csv --md research.md --niche "<niche>"`. Posts rank by multiple over their own account's median (provided, or derived from 5+ posts). No baseline means unranked, never estimated.
5. **Read the winners.** For each post at 2x or more: watch/read it (the creator can paste the transcript or describe it) and write *why it worked* in terms of hook formula, format, structure, topic, emotion, and what the first 3 seconds showed. Fill the research log's "Why it worked" and "How to adapt" lines.
6. **Patterns.** Summarise what repeats across outliers (formula, format, topic, length, CTA). State sample sizes and confidence. One account's lucky post is not a pattern.
7. **Optional web context.** Use web search for platform changes or niche news. Label as secondary sources with links and dates.
8. **Save.** `python3 scripts/research_log.py observations.csv --save` adds to the reusable library (`--library` to view).
9. **Hand off.** Packet to reel-creator / carousel-creator: top formulas, 3-5 adaptable angles in the creator's niche, the evidence for each (multiples with baseline source).

## Decisions

- **What counts as "working":** multiple over the account's own median (default 2x, `--min-multiple`). Raw views favour big accounts and are a weaker signal; say so if that is all you have.
- **Baseline reliability:** provided > derived (5+ posts) > none. Show which one each rank used.
- **Followers instead of views:** views-per-follower is a much weaker signal; label it and do not mix it into the ranking.
- **Adapt vs copy:** keep the structure and the formula; change the topic angle, examples and wording to the creator's own. Run `core.py score --rubric originality draft.txt --refs source.txt` on adaptations; overlap above ~0.2 means rewrite.
- **Not enough data** (under ~20 posts or 3 accounts): present it as anecdotes, not patterns.

## Output format

```
RESEARCH: <niche>  ·  <n> posts from <k> accounts  ·  collected <date> by <method>

WHAT IS WORKING
1. <formula / format / topic pattern>: <n> outliers, median <x>x (baseline: provided/derived), confidence <low/med/higher>
   Why: <mechanism>   Adapt as: "<hook in the creator's niche>"
2. ...

TOP POSTS  (multiple, account, formula, hook, link)
UNRANKED   (no reliable baseline; hooks kept for reference)
GAPS       topics peers do not cover that the creator's audience asks about
DATA NOTES all metrics user-supplied, not verified; missing values left blank
```
Plus the research log (`research.md`) and the library entry.

## Quality checklist

- [ ] No scraping, logins or automation; the creator collected the data.
- [ ] Every metric copied, not estimated; blanks reported as blanks.
- [ ] Every rank states its baseline source.
- [ ] Patterns state sample sizes and confidence.
- [ ] Adaptations are original (originality check on any near-copy).
- [ ] Verified data and assumptions kept apart in the handoff.

## Errors and edge cases

- User asks you to scrape or "pull all reels from @x": decline briefly, offer the manual brief or the official API route (`../creator-core/references/safety.md`).
- Only view counts, no baselines: run anyway; everything lands in "unranked". Ask for 5+ posts per account or the account median to rank.
- Numbers shown as "1.2M" / "12,3K": research_log.py parses K/M; check locale commas.
- A competitor's outlier relies on something the creator cannot do (celebrity, budget): note it and skip it.
- Pasted screenshots: read the visible numbers only; mark anything unreadable as blank.

## Examples

`examples/observations.csv` (6 posts, 3 accounts):
```
8.76x  @crumbnotes   reel  hard_way      provided  Nobody warns new bakers that a fla...
3.20x  @weekendloaf  reel  confession    provided  I was wrong about feeding my start...
1.90x  @crumbnotes   reel  numbered_list provided  3 signs that your dough is ready t...
0.40x  @weekendloaf  reel  unclassified  provided  Hi everyone so today we're baking...
unranked: @rye_and_rise x2 (no baseline)
```
Good read: "Two of the three outliers are contrarian truth-telling formulas (hard_way, confession). n=4 ranked posts, low confidence; worth testing, not a rule."
Bad read: "Confession hooks get 3.2x more views", from one post.

## References

- `references/research-method.md`: the collection brief for the creator, column definitions, analysis questions.
