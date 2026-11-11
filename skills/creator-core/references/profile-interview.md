# Profile interview

Ask in batches of three or four. After each batch, write what you learned into
`profile.json` and move on. Stop when the creator wants to; everything is
optional except niche, audience, tone and language.

The fastest high-quality route: ask for three to five things the creator has
actually written or said (captions, reel transcripts, voice notes). Derive
tone, sentence habits and words from those, then confirm with them.

## Batch 1: who and for whom (feeds every skill)

1. In one sentence, what do you help people with? → `identity.one_liner`, `niche.primary`
2. Who exactly is it for? Push for specific: "photographers charging under $2,000", not "creatives". → `audience.who`, `audience.identity_terms`
3. What are they struggling with, in their words? → `audience.pains`
4. What language and variant do you post in? → `language`

## Batch 2: voice (feeds every writing skill and the humanizer)

1. Paste 3 captions or transcripts that sound most like you. → `voice.sample_texts`
2. Three words for how you sound on camera. → `voice.tone`, `voice.on_camera`
3. Words or phrases you would never say? → `voice.words_i_never_use`
4. Emoji: none, sparse, moderate, heavy? → `voice.emoji_policy`

## Batch 3: business (feeds CTAs, DMs, stories, profile audit)

1. What do you sell, if anything? Only what exists today. → `identity.offer`
2. What should someone do after watching? (keyword DM, link, follow) → `goals.cta`
3. The one goal for the next 90 days. → `goals.primary`
4. Proof you are happy to state publicly: numbers, clients, results, credentials. → `verified_facts` (each with a source and date)

## Batch 4: content (feeds planner and auditor)

1. Your 2-4 content pillars and rough shares. → `niche.pillars`
2. Posts per week you can sustain, and on which days. → `content.posts_per_week`, `content.posting_days`
3. Formats you like and avoid. → `content.formats_preferred`, `content.formats_avoid`
4. Phrases people search to find accounts like yours. → `audience.search_terms`

## Batch 5: look and limits (feeds carousels, reels, gate)

1. Colours, fonts, visual style. → `visual`
2. Topics that are off limits, required disclaimers, compliance notes. → `restrictions`

## Rules

- Write down what they say, not what sounds better.
- Never turn "I think it was around 40%" into a verified fact. Ask for the source or leave it out.
- If the creator is in a regulated niche (finance, health, legal), ask about disclaimers in batch 1.
- Re-run `python3 scripts/profile.py check` at the end and read back the completeness score.
