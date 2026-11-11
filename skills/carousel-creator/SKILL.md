---
name: carousel-creator
description: >-
  Build Instagram carousels: concepts, a cover headline that earns the swipe,
  slide-by-slide copy with storytelling continuity, visual design direction,
  alt text, and export-ready specs (a designer/Canva spec sheet plus 1080x1350
  SVG slides). Use when the user says "carousel", "swipe post", "slides",
  "turn this into a carousel", "cover slide", or has a list, framework, story
  or article that should become a multi-image post.
---

# carousel-creator

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- A list, framework, step-by-step, myth/truth, comparison, case study or story that people will want to keep.
- content-repurposer hands over an article or a list-shaped moment.

Not for: single-image posts (caption-writer handles the text), reels (reel-creator).

## Inputs

### Required
- The topic or source material.

### Optional
- Slide count (default 6-9), concept type, visual style overrides, existing brand template name.
- Source text to adapt (article, transcript excerpt) with its origin.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: audience, voice, visual colours/fonts, CTA keyword, verified facts.
2. **Concepts.** If the topic is open, offer 3 concepts, each with a type from `references/carousel-types.md`, the cover headline, and the promise. Pick or let the user pick.
3. **Cover.** Write 3-5 cover headlines (≤ 10 words, ≤ 60 chars), score them: `python3 scripts/core.py score --rubric hook covers.txt --split lines`. Keep the best; it must be readable in one glance at grid size.
4. **Outline.** One job per slide using the roles in `carousel.json` (cover, problem, point, step, example, proof, myth, truth, recap, cta). Every slide must make the next one necessary: end slides on an open loop, a number in a sequence, or a question the next slide answers.
5. **Copy.** Headline ≤ 12 words, body ≤ 45 words per slide. Concrete over clever. Proof slides use verified facts only, else `{{placeholder}}`.
6. **Design direction.** Per slide: layout (type-only, annotated screenshot, photo + caption, diagram), emphasis word, visual. Use profile colours and fonts. Alt text per slide.
7. **Spec file.** Write the carousel as JSON (format in `scripts/carousel.py --help`) and run `python3 scripts/carousel.py spec.json --md spec.md --svg slides/`. Fix every FAIL and WARN (overflow, long body, missing CTA, continuity breaks).
8. **Humanize and gate.** content-humanizer on the slide copy; `python3 scripts/core.py gate copy.txt --type carousel`.
9. **Hand off** to caption-writer (often job B: the caption expands the cover's promise).

## Decisions

- **Slide count:** as many as the idea needs and no more; 5-10 is typical. Instagram allows up to 20.
- **Type-only vs designed:** the SVGs are a clean type-only base. If the creator uses Canva/Figma templates, the spec sheet is the deliverable and the SVGs are a preview.
- **Last slide:** one ask (save, share, keyword). The second-to-last slide is often a recap that makes saving worth it.
- **Story carousels:** setup → turn → payoff across slides; check with `core.py score --rubric storytelling`.
- **Adapting someone else's carousel:** structure only; run the originality rubric with `--refs`.

## Output format

```
CAROUSEL: <title>  ·  <type>  ·  <n> slides  ·  1080x1350

COVER OPTIONS (scored)
1. <headline>  <score>  <- used
2. ...

| # | role | headline | body | visual / layout | alt text |
| 1 | cover | ... | | ... | ... |
...

DESIGN: bg <hex> · text <hex> · accent <hex> · font <name> · 96 px margins
FILES: spec.json · spec.md · slides/slide_01.svg ...
CHECKS: carousel.py <verdict> · storytelling <score> · gate <verdict>
```

## Quality checklist

- [ ] Cover ≤ 10 words, scored, readable at grid size.
- [ ] Each slide has one job and leads to the next.
- [ ] Body ≤ 45 words per slide; no overflow in the SVG render.
- [ ] Proof uses verified facts only.
- [ ] Last slide has one ask.
- [ ] Alt text on every slide.
- [ ] carousel.py: no FAIL; WARNs fixed or explained. Gate run.

## Errors and edge cases

- `FAIL count`: fewer than 2 or more than 20 slides. Split into a series or merge.
- `WARN overflow`: shorten the copy (preferred) or move text to the next slide.
- `WARN continuity`: a slide shares no key words with the rest; check it belongs.
- Invalid JSON spec: carousel.py says where; fix and re-run.
- No profile colours: default theme (white, near-black, blue); say so.

## Examples

`examples/good-carousel.json`: 7 slides (cover → problem → proof → 3 steps → CTA). carousel.py: READY,
cover hook 82, storytelling 75.
`examples/bad-carousel.json`: a 22-word cover (hook 60), a 57-word slide, no CTA, an off-topic slide → REVIEW
with five warnings, storytelling 46.

## References

- `references/carousel-types.md`: eight carousel types with slide plans and design notes.
