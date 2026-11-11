# Scoring engine

Every score in this system comes from one engine (`lib/igkit/engine.py`) reading
a JSON rubric (`config/rubrics/*.json`). Scores are heuristic assessments of
text structure. None of them predicts reach or virality, and every rubric says
what it cannot see in its `limitations`.

## The rubrics

| rubric | measures | main limitation |
| --- | --- | --- |
| hook | first line: brevity, front-loading, specificity, stakes, aimed at someone | cannot see delivery or the first frame |
| caption | visible window, one ask, search phrases, hashtags, readability | truncation is approximate |
| storytelling | setup / turn / payoff, detail, tension, rhythm, landing | arc detected from marker phrases |
| engagement | ask, save-worthiness, share-worthiness, conversation, specificity | not a reach prediction; compare drafts of one post |
| originality | stock phrasing, overlap with reference posts | only knows the references you pass |
| human | slop, template constructions, rhythm, variety, hedges, dashes, banned words | not an AI detector; guarantees nothing about detectors |
| comment | not generic, about this post, length, adds something, no promo | needs `--post` for specificity |
| dm | personal, brief, one question, no pressure, no placeholders | needs `--post` for personalisation |
| bio | fits 150, who + what, next step, search phrase | cannot see photo, name field, highlights |

## Rubric format

```json
{
  "id": "hook", "name": "Hook strength", "version": 1,
  "measures": "one sentence",
  "limitations": ["what it cannot see", "..."],
  "bands": {"strong": 80, "ok": 55},
  "criteria": [
    {"id": "brevity", "label": "Brevity", "weight": 15, "measures": "...",
     "rules": [
       {"feature": "word_count", "type": "range", "ideal": [5, 14], "zero_at": [1, 28],
        "why": "shown in every report", "fix": "shown when the rule scores < 70",
        "unmeasured": "shown when the feature returns None"}
     ]}
  ],
  "dealbreakers": [
    {"id": "greeting", "feature": "starts_with_greeting", "op": "==", "value": true, "cap": 25, "message": "..."}
  ]
}
```

Rule types:
- `range` 100 inside `ideal`, falling linearly to 0 at `zero_at`.
- `max` lower is better: 100 at or below `good`, 0 at `zero_at`.
- `min` higher is better: 0 at or below `zero_at`, 100 at `good`.
- `bool` fixed score for `true` / `false`.

Criterion score = weighted mean of its measurable rules. Total = weighted mean
of measurable criteria, renormalised (the report states the measured share).
Dealbreakers cap the total.

## Features

Defined in `lib/igkit/features.py`, each `f(text, ctx) -> value | None`:

counts: `char_count word_count sentence_count line_count first_line_chars first_line_words mean_sentence_words`
openers: `starts_with_greeting starts_with_filler starts_with_emoji starts_with_hashtag`
specificity: `has_number specificity_hits specificity_density`
address: `second_person second_person_density first_person audience_hit`
stakes: `tension curiosity stakes`
asks: `ask_count has_ask closing_ask question_count`
language: `slop_count slop_density tell_count hedge_count hedge_density dash_count triad_count banned_hits`
rhythm: `burstiness mattr repeated_trigram_ratio repeated_opener_share`
platform: `hashtag_count generic_hashtag_count link_count mention_count emoji_count emoji_per_100_chars invisible_count`
search: `keyword_coverage keyword_in_visible`
story: `story_arc value_markers numbered_lines`
context: `context_overlap ref_overlap formula_match`
safety: `self_promo spam_count pushy_count generic_comment unverified_claims placeholder_count attention_begging engagement_bait`

## Tuning

- Edit the JSON in `config/rubrics/`, or put an override at `~/.creator-content-kit/rubrics/<id>.json` (same format).
- Word lists live in `config/lexicon.json` (override at `~/.creator-content-kit/config/lexicon.json`).
- `python3 -m unittest discover -s tests` at the repo root validates every rubric (unknown features, missing `why`, bad weights) and checks that the labelled good/bad examples still land on the right side.

## Reporting a score

Say: the number and band, what it measures, the weakest criterion and its fix,
and the limitation that matters here. Never: "this will perform", "viral score",
"guaranteed".
