# Workflows

Each skill has one job. A workflow is the shortest chain of jobs that answers
the request. Skip any step whose output already exists or that the user did
not ask for.

## Rules for every pipeline

1. Read the profile once at the start (`core.py profile show`); every step uses it.
2. Between steps, carry a handoff packet: `core.py handoff new --from A --to B --task "..."`.
   Fill `payload` (what the next step needs), `verified` (facts with a source),
   `assumptions` (anything inferred) and `open_questions`. Validate with
   `core.py handoff validate packet.json`.
3. A later step never upgrades an assumption to a fact.
4. The gate runs on every final artifact, by type.
5. The pipeline ends at **user approval**. Nothing is posted, scheduled or sent unless the creator then publishes the approved post with content-publisher and its approval code.

## Pipeline 1: topic to finished reel

```
topic
  -> viral-researcher      (optional: only if the user wants research, or no angle is clear)
  -> reel-creator       hooks -> scored -> script -> beat sheet
  -> caption-writer    caption for the reel (job A: the video carries the hook)
  -> content-humanizer      on the script and the caption
  -> creator-core gate  --type reel (script), --type caption (caption)
  -> user approval
```
Handoff viral-researcher -> reel-creator: `payload.formulas` (top formula ids), `payload.examples`
(research-log entries with multiples and baseline source), `verified` (only user-supplied
metrics, labelled as such).

## Pipeline 2: long video to a week of content

```
transcript (SRT/VTT/text)
  -> content-repurposer  segment.py shortlist -> pick 3-5 moments -> map to formats
  -> reel-creator       one script per reel moment (quote-faithful)
  -> carousel-creator   one carousel per list/framework moment
  -> caption-writer    caption per piece
  -> content-humanizer      all drafts
  -> content-planner       slot each piece into the calendar (status: drafted)
  -> creator-core gate  per piece
  -> user approval
```
Handoff content-repurposer -> reel-creator / carousel-creator: `payload.moments` with
timestamps and the exact source sentences. Every derivative keeps its source
timestamp so the creator can check nothing was put in their mouth.

## Pipeline 3: weekly cycle

```
performance-auditor (last 2-4 weeks, if data exists)
  -> content-planner       plan next week; weight formats/pillars by what the audit found (n >= 3 only)
  -> reel-creator / carousel-creator / story-strategist per slot
  -> caption-writer -> content-humanizer -> gate
  -> user approval, then calendar status -> approved (only when the user says so)
```

## Pipeline 4: inbox session

```
comments -> reply-assistant triage -> replies (gate --type reply)
leads / keyword requests -> dm-assistant (dm.py lint) -> user sends
```

## When not to chain

- "Write me a caption" -> caption-writer alone (it calls content-humanizer and the gate inline).
- "Score these hooks" -> reel-creator's hook_rank.py alone.
- Research the user did not ask for is cost without value. Offer it in one line instead.
