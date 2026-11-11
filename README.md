# creator-content-kit

A set of 13 agent skills plus a shared core that help one Instagram creator plan, write, check and improve their own content. It drafts reels, captions, carousels, stories, comments, replies and DMs, researches the niche, audits the profile and past posts, and keeps the content calendar.

Each skill is a folder with a `SKILL.md` an agent reads, plus small Python tools the agent runs to score, lint, time and validate drafts. Every skill reads one shared creator profile, so voice, audience, pillars and the facts the creator has verified carry across all of them.

**What it never does:** log in to Instagram, ask for or store passwords, post or send anything, scrape, or automate follows, likes, comments or DMs. Every output is a copy-ready draft. The creator reviews it and posts it themselves. See [safety](skills/creator-core/references/safety.md).

---

## Contents

- [Skills](#skills)
- [Installation](#installation)
- [Set up the creator profile](#set-up-the-creator-profile)
- [Using the skills](#using-the-skills)
- [Architecture](#architecture)
- [Quality scoring](#quality-scoring)
- [Running the utilities directly](#running-the-utilities-directly)
- [Adding a skill](#adding-a-skill)
- [Tests](#tests)
- [Supported environments](#supported-environments)
- [Limitations](#limitations)

---

## Skills

| Skill | Does | Tool(s) |
|---|---|---|
| `creator-core` | Creator profile setup, rubric scoring, final quality gate, multi-skill pipelines, handoff packets | `profile.py` `score.py` `gate.py` `handoff.py` `claims.py` |
| `reel-creator` | Idea angles, hooks scored against a 24-formula library, script, scene breakdown, timed beat sheet, caption, CTA | `hook_rank.py` `script_timer.py` |
| `viral-researcher` | Niche research from observations the creator collects; ranks posts by how far they beat their own account's baseline; reusable research log | `research_log.py` |
| `caption-writer` | Captions built for the ~125-character preview, search phrases, hashtags within the cap, CTA variants, feed preview | `caption_lint.py` |
| `carousel-creator` | Concepts, cover, slide copy, design direction, alt text, designer spec sheet, 1080x1350 SVG slides | `carousel.py` |
| `story-strategist` | Daily frame sequences, sticker choice, story-to-DM funnels, storyboard | `story.py` |
| `profile-auditor` | Profile audit out of 100 on a 10-part rubric, prioritised fixes, bio and name-field rewrites | `profile_audit.py` |
| `content-planner` | Weekly/monthly calendar, content-mix balance across pillars, idea backlog, publishing status, CSV/Markdown export | `planner.py` |
| `content-humanizer` | Removes invisible characters and clause dashes; flags AI-sounding vocabulary, templates, hedges, monotone rhythm; checks the creator's voice survived a rewrite | `rewrite_check.py` |
| `comment-assistant` | Thoughtful comments on other creators' posts (add a point, real question, short experience, respectful pushback) | core `score.py --rubric comment` |
| `reply-assistant` | Triage comments on the creator's own posts (lead, support, keyword, question, pushback, praise, spam) and draft replies in order | `triage.py` |
| `dm-assistant` | Keyword delivery, inbound replies, personal first messages, collab proposals, max two follow-ups; checks the messaging-window rules | `dm.py` |
| `content-repurposer` | Finds clip-worthy moments in a YouTube/podcast/webinar transcript (SRT, VTT or plain text) and maps them to reels and carousels | `segment.py` |
| `performance-auditor` | Post-mortem from the creator's own Insights / Meta Business Suite CSV export: rates per reach, watch ratio, outliers, patterns by format, pillar, hook and weekday | `audit.py` |

Each `SKILL.md` has the same sections: description and activation triggers, required and optional inputs, workflow, decision rules, output format, quality checklist, error handling and examples. Longer material lives in `references/` and is only read when needed (progressive disclosure). Each skill also ships good and bad examples in `examples/`.

---

## Installation

You need Python 3.8+ and nothing else. The tools use only the standard library.

Skills look for `creator-core` beside them, so install them **side by side**. Every method below does that.

### Claude Code: plugin

```text
/plugin marketplace add /path/to/creator-content-kit
/plugin install creator-content-kit@creator-content-kit
```

Use the repo path, or its git URL once you have pushed it somewhere.

### Claude Code: copy into a skills folder

```sh
scripts/install.sh                     # ~/.claude/skills/  (all projects)
scripts/install.sh --project ~/my-app  # ~/my-app/.claude/skills/  (one project)
scripts/install.sh --link              # symlink instead of copy, so edits here apply at once
```

### Claude.ai / Claude desktop app (upload one skill at a time)

```sh
python3 scripts/package.py              # dist/<skill>.zip for every skill
python3 scripts/package.py reel-creator caption-writer
```

Each zip is self-contained: it carries its own copy of the core library in `_core/`. Upload the zips under Settings > Capabilities > Skills. If you upload several, each still works on its own.

### Other agents

```sh
scripts/install.sh --dest /path/the/agent/reads/skills/from
```

Any agent that can read a `SKILL.md`, follow it and run `python3` can use these. See [supported environments](#supported-environments).

---

## Set up the creator profile

Every skill reads one profile first. Create it once:

```sh
python3 skills/creator-core/scripts/profile.py init      # profile.json + voice.md, brand.md, audience.md, content-strategy.md
python3 skills/creator-core/scripts/profile.py check     # schema errors + completeness score + most useful missing fields
python3 skills/creator-core/scripts/profile.py show      # the brief every skill reads
```

Or just ask the agent: *"set up my Instagram creator profile"*. `creator-core` interviews you a few questions at a time ([interview guide](skills/creator-core/references/profile-interview.md)).

**Where the profile lives** (first match wins; `profile.py where` tells you which):

1. `--profile path/to/profile.json`
2. `$IG_PROFILE`
3. `.creator-content-kit/profile.json` in the current folder or any parent (one per project/brand)
4. `$IG_AGENT_HOME/profile.json`, default `~/.creator-content-kit/profile.json`

**What it holds:** identity, niche, audience (including the phrases they search), positioning, language, tone, personality, phrases you use and words you never use, content pillars with target shares, formats, posting days and times, visual identity (colours and fonts, used by the carousel SVGs), restrictions (things never to say, off-limits topics, required disclaimers), goals and the CTA keyword.

**`verified_facts`** is the field that matters most. Put every number, result, client, credential or story you are happy to state publicly there, with a source. The quality gate **blocks** any draft that states a metric, achievement, testimonial or credential not found in that list. Instead, skills write placeholders such as `{{your result}}` for you to fill. Nothing is ever invented.

The template is at [`templates/profile.json`](templates/profile.json), with the markdown companions beside it. A complete fictional example is in [`tests/fixtures/profile.json`](tests/fixtures/profile.json).

---

## Using the skills

Ask in plain language. Each skill's description lists the requests that trigger it:

- *"Write me a reel about why home bakers shouldn't feed their starter at midnight."*
- *"Here's my caption. Make the first line stronger and check the hashtags."*
- *"Turn this podcast transcript into 3 reels and a carousel."*
- *"Audit my profile."* (paste your bio, name field, link, highlight names)
- *"Plan December. Four posts a week."*
- *"Here are 40 comments from yesterday's post. What should I reply to first?"*
- *"Does this read like AI? Fix it but keep my voice."*

In Claude Code you can also call a skill directly: `/reel-creator`, `/caption-writer` and so on.

### Pipelines

`creator-core` chains skills for bigger jobs and skips any step whose output already exists. The full list is in [workflows](skills/creator-core/references/workflows.md):

```text
topic -> viral-researcher (research) -> reel-creator (hooks -> score -> script) -> caption-writer -> content-humanizer -> gate -> creator approves
YouTube transcript -> content-repurposer -> reel-creator + carousel-creator -> caption-writer -> content-planner (slots)
Insights export -> performance-auditor -> content-planner (rebalance mix) -> reel-creator / carousel-creator briefs
```

Skills pass JSON **handoff packets** to each other ([schema](skills/creator-core/config/handoff.schema.json), [example](skills/creator-core/examples/handoff-example.json)). Each packet keeps `payload`, `verified` (facts with sources) and `assumptions` in separate fields, so a guess never quietly becomes a fact downstream.

### Approval

Nothing reaches the creator as "final" until the gate has run:

```sh
python3 skills/creator-core/scripts/gate.py draft.txt --type caption
```

| Verdict | Exit | Meaning |
|---|---|---|
| `READY` | 0 | Present it. The creator still decides and posts it. |
| `REVIEW` | 1 | Present it with every warning stated (e.g. "fill `{{amount}}`"). |
| `BLOCKED` | 2 | Fix it first: an unverified claim, a banned word, invisible characters, over the caption limit, a hook below threshold... |

---

## Architecture

```text
creator-content-kit/
├── .claude-plugin/            plugin.json + marketplace.json (Claude Code plugin)
├── skills/
│   ├── creator-core/               shared foundation (also a skill itself)
│   │   ├── SKILL.md
│   │   ├── lib/igkit/         Python library: text, lexicon, features, engine, claims, profile, schema, report
│   │   ├── lib/shims/         canonical _bootstrap.py + core.py copied into every skill
│   │   ├── config/            lexicon, platform limits, hook formulas, rubrics/, gate rules, JSON schemas
│   │   ├── templates/         profile.json + voice/brand/audience/content-strategy.md
│   │   ├── scripts/           profile, score, gate, handoff, claims
│   │   └── references/        interview guide, workflows, scoring, safety
│   └── <skill>/
│       ├── SKILL.md           <= 260 lines; the always-loaded part
│       ├── references/        loaded only when the workflow says so
│       ├── scripts/           the skill's tool(s) + _bootstrap.py + core.py
│       ├── examples/          good/bad samples + cases.json (expected outputs, run by the tests)
│       └── *.json             skill-specific config (e.g. content-planner/mix.json)
├── templates -> skills/creator-core/templates
├── scripts/                   install.sh, package.py, new_skill.py, validate_skills.py, sync_shims.py
├── tests/                     unittest suite + fixtures
└── docs/                      architecture, adding a skill, testing
```

Main ideas, covered in [docs/architecture.md](docs/architecture.md):

- **One shared library, no copies.** Each skill's `scripts/_bootstrap.py` finds `creator-core` through `$IG_CORE_DIR`, then a vendored `_core/` (packaged zips), then a sibling `../creator-core`. `scripts/core.py` in every skill runs the core tools, so a skill's instructions can say `python3 scripts/core.py gate draft.txt` wherever it is installed.
- **Behaviour lives in JSON.** Slop words, hook formulas, rubric weights, gate thresholds and platform limits are config files. Override any of them per user by putting a file with the same name in `~/.creator-content-kit/config/` or `~/.creator-content-kit/rubrics/`.
- **Verified vs assumed is structural.** The profile's `verified_facts`, the claims checker, the gate and the handoff packets all keep facts the creator confirmed apart from everything else.
- **Platform facts carry a confidence level.** Every entry in [`platform.json`](skills/creator-core/config/platform.json) is marked `high`, `medium` or `verify`. Skills mention the `verify` ones (e.g. the hashtag cap) instead of stating them as fact.

---

## Quality scoring

Nine JSON rubrics in [`skills/creator-core/config/rubrics/`](skills/creator-core/config/rubrics/): `hook`, `caption`, `originality`, `storytelling`, `engagement`, `human`, `comment`, `dm`, `bio`.

```sh
python3 skills/creator-core/scripts/score.py --list
python3 skills/creator-core/scripts/score.py --rubric hook --split lines hooks.txt   # rank several options
```

Each result shows:

- the 0-100 score and its band (`strong` >= 80, `ok` >= 55, `weak`);
- every criterion, with **what it measures**, the measured value, and a **fix** when it lost points;
- **dealbreakers** that capped the score (e.g. a hook that opens with a greeting is capped at 25);
- the share of the rubric that could actually be measured, since features that don't apply are skipped and the score is re-normalised rather than guessed;
- the rubric's **limitations**, in plain words.

These scores are text heuristics. They catch weak openings, vague claims, filler, AI-sounding patterns and missing asks. They **cannot** predict reach or virality, judge visuals or delivery, or tell whether an idea is actually good. No skill claims otherwise, and none claims its output will pass an AI detector. Details and calibration notes: [scoring](skills/creator-core/references/scoring.md).

To tune a rubric, copy it to `~/.creator-content-kit/rubrics/<id>.json` and change weights, ranges or dealbreakers. `score.py` validates the file and reports any mistakes in it.

---

## Running the utilities directly

All tools take `--help`, accept `-` for stdin, and most take `--json` for machine-readable output. Run them from inside the skill folder (this is how the skills invoke them):

```sh
cd skills/reel-creator
python3 scripts/hook_rank.py examples/hooks-good.txt              # rank hooks, say-time, formula match
python3 scripts/hook_rank.py --formulas --family contrarian       # browse the formula library
python3 scripts/script_timer.py examples/good-script.txt --target 30     # timed beat sheet + pacing flags

cd ../caption-writer && python3 scripts/caption_lint.py examples/good-caption.txt
cd ../carousel-creator && python3 scripts/carousel.py examples/good-carousel.json --svg /tmp/slides
cd ../content-planner && python3 scripts/planner.py plan --month 2026-12 && python3 scripts/planner.py list
cd ../content-humanizer && python3 scripts/rewrite_check.py report examples/before.txt
cd ../content-repurposer && python3 scripts/segment.py examples/episode.srt --top 5
cd ../performance-auditor && python3 scripts/audit.py examples/posts.csv
cd ../dm-assistant && python3 scripts/dm.py lint examples/good-collab.txt --kind collab
cd ../creator-core && python3 scripts/gate.py examples/draft-unverified.txt --type caption
```

Exit codes: `0` ok/READY, `1` REVIEW / warnings, `2` BLOCKED / bad input, `3` no creator profile found.

Files the tools keep (the calendar, the research library) live in `$IG_AGENT_HOME/workspace/` (default `~/.creator-content-kit/workspace/`), or wherever you point `--file`.

---

## Adding a skill

```sh
python3 scripts/new_skill.py collab-scout "Find and pitch collaboration partners"
# edit skills/collab-scout/SKILL.md, references/, scripts/tool.py, examples/
python3 scripts/validate_skills.py collab-scout
python3 -m unittest discover -s tests
```

The scaffold already passes validation. Its starter tool reads the profile and uses the scoring engine. The full contract, including new rubrics and new gate types, is in [docs/adding-a-skill.md](docs/adding-a-skill.md).

---

## Tests

```sh
python3 -m unittest discover -s tests          # 85 tests, ~3 s, standard library only
python3 scripts/validate_skills.py             # SKILL.md contract for every skill
python3 scripts/sync_shims.py --check          # every skill's shims match the canonical copy
```

The suite covers:

| File | Covers |
|---|---|
| `test_text.py` | tokenising, sentences, emoji, speech timing, burstiness, truncation |
| `test_lexicon_claims.py` | slop/tell detection, invisible characters, CTA detection, claim extraction and verification |
| `test_engine.py` | rubric scoring, renormalisation, dealbreakers, hook ordering, explanations |
| `test_profile.py` | profile resolution order, schema validation, completeness, the brief |
| `test_configs.py` | every JSON file parses; platform confidence levels; each hook formula matches its own example; gate types point at real rubrics; skill configs are consistent |
| `test_tools.py` | each skill's utility: caption lint, beat timing, hook ranking, research-log baselines, triage, planner cycle, humanizer, carousel SVG, story funnel, profile audit, DM rules, transcript parsing, Insights parsing, gate |
| `test_skills.py` | every skill meets the SKILL.md contract; the validator catches broken skills; no virality/detector promises; passwords are only mentioned to refuse them |
| `test_examples.py` | runs every `examples/cases.json`: each tool's output on the shipped examples must match the expected values (output consistency) |
| `test_packaging.py` | zips run without a sibling core; side-by-side install works; the scaffold validates; no network modules; standard library only |

More in [docs/testing.md](docs/testing.md).

---

## Supported environments

| Environment | How | Status |
|---|---|---|
| Claude Code (CLI, desktop, IDE extensions) | plugin, `install.sh`, or `install.sh --project` | Layout follows the Claude Code skills/plugin format; the tools were run and tested from a terminal here |
| Claude.ai / Claude desktop app | `package.py` zips uploaded as custom skills | Zips tested to run standalone; the upload itself is done by you |
| Claude Agent SDK | point the SDK's skills directory at an `install.sh --dest` folder | Same files as above |
| Other agents (Codex, Cursor, Gemini CLI, etc.) | `install.sh --dest`, or reference the `SKILL.md` from the agent's instructions file | Needs an agent that reads markdown and can run `python3`; not tested here |
| No agent | run the scripts yourself | Everything under [Running the utilities](#running-the-utilities-directly) works |

Tested on macOS with Python 3.15. The code avoids features newer than 3.8.

---

## Limitations

- **Scores are heuristics**, not predictions. A 95 means the text avoids common problems; it does not mean the post will perform.
- **English only** for the lexicons and rubrics. Other languages get limits and structure checks, but not reliable slop/tone scoring.
- **Platform rules change.** The 5-hashtag cap is marked `verify` because sources disagree. Re-check anything marked `verify`/`medium` in `platform.json` and update the file.
- **No live data.** Research and audits only see what the creator gives them: observations they collect and exports they download. That is a deliberate safety choice.
- **Profile and visual quality** (photo, video delivery, design taste) are scored only when the creator or the agent's own judgement supplies a manual score, and the output says so.

## License

[MIT](LICENSE)
