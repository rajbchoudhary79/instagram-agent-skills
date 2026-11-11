# Adding a skill

## 1. Scaffold

```sh
python3 scripts/new_skill.py collab-scout "Find and pitch collaboration partners"
```

This creates `skills/collab-scout/` with:

- `SKILL.md`, which has every required section filled with guidance to replace
- `references/guide.md`
- `scripts/tool.py`, a working starter that reads the profile and scores with the `human` rubric
- `scripts/_bootstrap.py` and `scripts/core.py`, the shared shims (don't edit them; see step 5)
- `examples/good.txt` and `examples/cases.json`

It passes `validate_skills.py` straight away.

## 2. Write SKILL.md

The validator checks these:

- Frontmatter `name` equals the folder name. `description` is at most 1024 characters and includes **"Use when ..."** followed by the requests that should trigger the skill.
- Sections: `## When to use`, `## Inputs` with `### Required` and `### Optional`, `## Workflow`, `## Decisions`, `## Output format`, `## Quality checklist`, `## Errors and edge cases`, `## Examples`.
- At most 260 lines. Move longer material into `references/` and point to it from the workflow step that needs it.
- Every `references/...`, `scripts/...`, `examples/...` path written in backticks must exist.

Conventions used by every existing skill:

- Workflow step 1 reads the profile (`python3 scripts/core.py profile show`). On exit 3 (no profile), ask the minimum questions and label the answers as assumptions.
- Never invent results, numbers, clients or stories. Use `{{placeholders}}`.
- End with the gate: `python3 scripts/core.py gate draft.txt --type <type>`.
- The output is a copy-ready block for the creator to post or send. A new skill never posts or sends anything; publishing goes through content-publisher and its approval code.

## 3. Write the tool

```python
import _bootstrap  # noqa: F401   (must come before igkit imports)
from igkit import cli, engine, features, paths, profile, report as R, text as T
```

Useful pieces:

- `cli.add_common(ap)` + `cli.build_ctx(args)` → profile-aware scoring context
- `engine.score(text, "<rubric>", ctx)` / `engine.render(result)`
- `paths.load_config("<name>")` for core config; `paths.load_json(os.path.join(SKILL_DIR, "x.json"))` for your own
- `paths.workspace_dir()` for files the tool keeps
- `R.emit_json(obj)` for `--json`, and `R.verdict(checks)` for `{id, level, message}` lists

Keep to the shared exit codes: 0 ok, 1 warnings, 2 blocked or bad input, 3 no profile. Support `--help`, `--json`, and `-` for stdin. Use the standard library only.

## 4. Add a rubric or gate type (optional)

**Rubric:** add `skills/creator-core/config/rubrics/<id>.json`:

```json
{
  "id": "collab", "name": "Collab pitch", "version": 1,
  "measures": "...", "limitations": ["..."],
  "bands": {"strong": 80, "ok": 55},
  "criteria": [
    {"id": "personal", "label": "Personal", "weight": 40, "measures": "...",
     "rules": [{"feature": "context_overlap", "type": "min", "zero_at": 0, "good": 3,
                "why": "...", "fix": "...", "unmeasured": "no --post given"}]}
  ],
  "dealbreakers": [
    {"id": "pushy", "feature": "pushy_dm", "op": ">=", "value": 1, "cap": 50, "message": "..."}
  ]
}
```

Rule types:

| type | fields | scores 100 when | scores 0 at |
|---|---|---|---|
| `min` | `good`, `zero_at` | value ≥ `good` | `zero_at` (linear between) |
| `max` | `good`, `zero_at` | value ≤ `good` | `zero_at` |
| `range` | `ideal: [lo, hi]`, `zero_at: [lo0, hi0]` | inside `ideal` | `lo0` / `hi0` |
| `bool` | `true`, `false` | n/a: returns the given score | |

`feature` must be a name in `igkit/features.py` `FEATURES`. To add a new measurement, add a function there and a test. `score.py --rubric collab` checks the rubric before scoring.

**Gate type:** add an entry to `skills/creator-core/config/gate.json` `types`, listing rubric thresholds, `first_line` hook thresholds and which `limits` apply.

## 5. Shared code

Never edit a skill's `_bootstrap.py` or `core.py` directly. Edit `skills/creator-core/lib/shims/`, then:

```sh
python3 scripts/sync_shims.py          # copy to every skill
python3 scripts/sync_shims.py --check  # CI: fails if any skill is out of date
```

## 6. Examples and expected outputs

Add good and bad examples, then describe what the tool must report about them in `examples/cases.json`:

```json
{"cases": [
  {"name": "good pitch passes", "run": ["scripts/tool.py", "examples/good.txt", "--json"],
   "expect": [{"path": "human.score", "op": ">=", "value": 80}]},
  {"name": "invented result is blocked", "run": ["scripts/core.py", "gate", "examples/bad.txt", "--type", "dm"],
   "exit": 2}
]}
```

`tests/test_examples.py` runs these with the fixture profile. Paths are dotted (`checks.0.id`, `ranked.-1.score`). The ops are listed at the top of that file.

## 7. Check

```sh
python3 scripts/validate_skills.py collab-scout
python3 -m unittest discover -s tests
```

`test_skills.py` has a fixed list of expected skills. Add the new name to `EXPECTED` there.
