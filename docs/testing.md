# Testing

```sh
python3 -m unittest discover -s tests                         # whole suite
python3 -m unittest discover -s tests -p "test_tools.py"      # one file
python3 -m unittest tests.test_engine -k hook                 # (from repo root, with tests/ on the path) one area
python3 -W error::ResourceWarning -m unittest discover -s tests   # strict: unclosed files fail
```

Standard library `unittest`. No pytest, no dependencies. It runs in about 3 seconds.

## Isolation

`tests/helpers.py` runs before any test and:

- points `IG_AGENT_HOME` at a fresh temporary directory, so the suite never reads or writes `~/.creator-content-kit`;
- points `IG_PROFILE` at `tests/fixtures/profile.json`, a fictional creator ("Priya Nair", sourdough for busy home bakers) with three verified facts;
- puts `creator-core/lib` on `sys.path`.

`helpers.run(skill, args)` runs a tool as a subprocess from inside the skill folder, which is how an agent runs it. `helpers.load_script(skill, name)` imports a tool as a module so its functions can be unit-tested.

## What each layer proves

| layer | proves |
|---|---|
| unit (`test_text`, `test_lexicon_claims`, `test_engine`, `test_profile`) | the measurements are right on hand-checked inputs, including the edge cases that broke during development (emoji ZWJ sequences, curly apostrophes, `$60.` at a sentence end, "what kind of project" not being a hedge) |
| config (`test_configs`) | every JSON file parses and is internally consistent. Each hook formula's regex matches its own example. Proof-family hooks use placeholders instead of invented numbers. |
| tools (`test_tools`) | each skill's utility, function by function |
| contract (`test_skills`) | every SKILL.md has the required sections and valid references. The validator itself catches a broken skill. Wording never promises virality or detector bypass, and passwords are only mentioned to refuse them. |
| output consistency (`test_examples`) | each skill's shipped examples produce the documented results (scores, verdicts, exit codes) |
| install (`test_packaging`) | zips run standalone, side-by-side installs work, the scaffold validates, no network imports, standard library only |

## When a calibration test fails

Scores are heuristics tuned against the examples. If you change a word list or rubric and `test_examples` fails:

1. Run the failing case's command by hand without `--json` to read the explanation.
2. Decide which is wrong, the change or the expectation. A good example should still clearly beat its bad counterpart.
3. Update `cases.json` **and** any numbers quoted in that skill's SKILL.md `## Examples`, so the documentation matches what the tools really output.
