# Architecture

## Layers

```text
 agent reads SKILL.md  ──►  follows Workflow  ──►  runs scripts/<tool>.py  ──►  igkit (creator-core/lib)
                                                                                 │
                     creator profile  ◄── profile.py ◄───────────────────────────┤
                     config/*.json    ◄── paths.load_config (+ user overrides) ◄─┘
```

1. **Instructions** (`SKILL.md` + `references/`): what to ask, what to decide, what to output. The agent's judgement lives here.
2. **Tools** (`scripts/*.py`): deterministic checks the agent runs on its own drafts: counts, timings, limits, scores, file formats. Everything a tool can measure, it measures, so the agent doesn't have to estimate it.
3. **Library** (`creator-core/lib/igkit`): text analysis, the rubric engine, the claims checker, profile loading, schema validation and report formatting. Shared by every tool.
4. **Config** (`creator-core/config`, plus a few per-skill JSON files): word lists, formulas, rubrics, thresholds and platform limits. Changing behaviour means editing JSON, not code.

## igkit modules

| module | job |
|---|---|
| `paths` | locate the core, config files and user overrides (`$IG_AGENT_HOME/config/<name>.json`), workspace directory, `-` = stdin |
| `text` | tokens, sentences, emoji (ZWJ sequences, skin tones), hashtags, mentions, links, `{{placeholders}}`, speech and reading time, burstiness, MATTR, repetition, truncation |
| `lexicon` | word-bounded matching against `lexicon.json`: slop, hedges, greetings, bait, generic comments, spam, AI-template tells, invisible characters, asks |
| `features` | ~60 named measurements (`word_count`, `stakes`, `specificity_hits`, `unverified_claims`, ...) that rubrics refer to by name |
| `engine` | loads and checks rubrics, scores text, explains the result |
| `claims` | finds metrics, achievements, testimonials and credentials, and checks each one against `verified_facts` |
| `profile` | resolves, loads, validates and summarises the creator profile |
| `schema` | a small JSON-Schema validator (no dependencies) |
| `report` | terminal tables, bars, verdicts, JSON output |
| `cli` | common flags (`--profile --no-profile --keywords --refs --post --json`) and building the scoring context |

## How a skill finds the core

`scripts/_bootstrap.py` is identical in every skill (kept in sync by `scripts/sync_shims.py`). It adds the first match to `sys.path`:

1. `$IG_CORE_DIR`
2. `<skill>/_core`, the vendored copy inside packaged zips
3. `<skill>` itself, when the skill is `creator-core`
4. `<skill>/../creator-core`, a side-by-side install

If none is found it exits with code 2 and an explanation. `scripts/core.py` dispatches `profile | score | gate | handoff | claims` to the core tools, so a SKILL.md can always write `python3 scripts/core.py gate draft.txt` without knowing the install layout.

## Data the system keeps

| what | where |
|---|---|
| creator profile + companions | resolved as described in the README (`profile.py where`) |
| config / rubric overrides | `$IG_AGENT_HOME/config/`, `$IG_AGENT_HOME/rubrics/` |
| content calendar | `$IG_AGENT_HOME/workspace/calendar.json` (or `--file`) |
| research library | `$IG_AGENT_HOME/workspace/research-library.json` (or `--library`) |

`$IG_AGENT_HOME` defaults to `~/.creator-content-kit`. Nothing is sent anywhere. The test suite checks that no script imports a network module.

## Verified vs assumed

A fact has to be confirmed by the creator before any skill states it:

- **Profile:** `verified_facts[]` holds facts with a source. Everything else in the profile is about tone and preference, not claims.
- **Claims checker:** extracts metrics ("40%", "$50,000", "3x"), achievements ("I built", "we grew"), testimonials and credentials. A claim counts as verified when its numbers all appear in one verified fact, or when it shares ≥60% of its content words with one.
- **Gate:** an unverified metric, achievement or testimonial makes a draft BLOCKED; an unverified credential makes it REVIEW. `{{placeholders}}` are allowed and listed for the creator to fill.
- **Handoff packets:** `verified` and `assumptions` are separate arrays, and research results carry their own confidence (`research_log.py` labels baselines as provided, derived or missing).

## Platform facts

`platform.json` stores each limit as `{"value", "confidence", "note"}`. `high` means stable and documented. `medium` means it varies by account or region. `verify` means sources disagree or it changed recently. Skills tell the creator to check anything marked `verify`. Update the file when Instagram changes something. Nothing in the code hard-codes these values.

## Design choices

- **Standard library only:** installs anywhere `python3` exists, packages into a zip, and has nothing to update.
- **Heuristics with explanations, not black boxes:** every rule has a `why` and a `fix`, every rubric lists `limitations`, and unmeasurable features are skipped (and reported) instead of guessed.
- **Tools never write content:** they measure. Writing is the agent's job, in the creator's voice, guided by the SKILL.md.
- **No unnecessary agent calls:** pipelines skip steps whose output exists, and skills share one profile read instead of re-asking.
