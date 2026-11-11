# Research method

## The collection brief (send this to the creator)

> Pick 5-10 accounts in your niche that are a bit ahead of you, not celebrities.
> For each, open the Reels tab and go through the last 12-15 reels at normal speed.
> For each reel, note: link, format, the first line (spoken or on screen), the
> topic in a few words, the view count shown, and anything else visible (likes,
> comments). If you know the account's typical views, note that too.
> Paste it here in any shape; I'll put it in a table.

Why the creator collects it: Instagram's terms prohibit scraping and automated
collection, and it gets accounts restricted. Reading at human speed in their own
session is ordinary use. The agent never logs in or asks for credentials.

Official alternative: an Instagram professional account with a Meta developer
app can use the Graph API `business_discovery` field to read public metrics of
other business/creator accounts. If the creator uses it, set `source` to
`graph-api business_discovery` and the date.

## Columns

| column | meaning | if missing |
| --- | --- | --- |
| url | permalink | fine, but dedupe is weaker |
| account | handle without @ | needed for baselines |
| format | reel / carousel / single | "unknown" |
| hook | first spoken line or on-screen text | formula = "no hook text" |
| topic | a few words | grouped as unknown |
| views | as shown in the app (K/M ok) | post cannot be ranked |
| likes, comments, shares, saves | as shown | left blank |
| account_median_views | the account's typical reel views | derived from 5+ posts, else unranked |
| followers | as shown | not used for ranking |
| posted | date | optional |
| source | how and when it was collected | "unspecified" |
| notes | anything observed: length, visuals, audio, CTA | optional |

## Questions to answer about each outlier

1. Hook: which formula? What did the first frame show? On-screen text?
2. Promise: what does the viewer get by staying?
3. Structure: which script structure (see reel-creator references)?
4. Specificity: what concrete details carried it?
5. Emotion: surprise, recognition, anger, relief, aspiration?
6. Format: length, face/no face, edit pace, text density.
7. CTA: what did it ask for? Did the comments do it?
8. Transferability: what does the creator have (verified) that makes their version credible?

## Reading the numbers honestly

- Multiples compare a post to its own account. They say "this did unusually well for them", not "this will do well for you".
- Fewer than 3 outliers sharing a trait is an anecdote.
- Views are distribution, not resonance. Comments and shares visible in the app hint at resonance; saves are usually not public.
- Recent posts have not finished accumulating views; note the post date.
