---
name: comment-assistant
description: >-
  Write thoughtful comments on other creators' Instagram posts: read the post's
  context, choose a comment style that fits (add a point, ask a real question,
  share a short experience, respectful pushback, specific praise, a useful
  resource in words), and check every comment is specific, non-generic and
  free of self-promotion. Use when the user says "comment on this", "what
  should I comment", "engage with this account", "help me network in the
  comments", or pastes someone else's post or reel.
---

# comment-assistant

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- The creator wants to engage with peers, potential collaborators or their audience's favourite accounts.
- content-planner lists accounts to engage with this week.

Not for: replies under the creator's own posts (reply-assistant), private messages (dm-assistant).

## Inputs

### Required
- The post: caption text and/or a description or transcript of the reel/carousel (the creator pastes it).

### Optional
- Who the account is (peer, bigger creator, potential client, brand).
- Existing top comments (to avoid repeating them).
- The creator's angle or experience on the topic.

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: voice, expertise, verified facts, words never used.
2. **Read the post.** Write one sentence on what it actually claims or shows, and the one detail most worth reacting to. Do not comment on what you have not been given.
3. **Pick a style** from `references/comment-styles.md` that fits the post and the relationship. Default: add a point or ask a real question.
4. **Draft 3 options**, each a different style, 6-40 words, referencing a specific detail from the post. The creator's experience only if verified or told to you now.
5. **Check.** Put the post text in a file and run `python3 scripts/core.py score --rubric comment option.txt --post post.txt` for each (or `--split blocks` on all three). Rewrite anything under 70 or with a dealbreaker (generic, promo, link, spam).
6. **Deliver** the options with a recommendation. The creator posts it themselves, one at a time, on posts they actually read.

## Decisions

- **Peer vs bigger account:** with peers, an experience or a question builds a relationship; with big accounts, an early, specific add-on point gets seen.
- **Disagreeing:** only with a reason and respect; one comment, no thread fights. Pushback should still be useful to readers.
- **Questions:** ask only what you want answered, answerable in a reply.
- **Never:** "Great post!", emoji-only, "check out my page", links, @-ing yourself, copy-pasted comments across posts, comments on posts not read.
- **Volume:** quality over count. Suggest a handful of thoughtful comments a day, not a quota. No automation of comments, ever.

## Output format

```
POST: <one-line summary of what it says>   DETAIL: <the specific thing to react to>

1. [add a point] <comment>                 comment score <n>   <- recommended
2. [question]    <comment>                 comment score <n>
3. [experience]  <comment>                 comment score <n>
```

## Quality checklist

- [ ] Based on the actual post text the creator provided.
- [ ] Each option references a specific detail from the post.
- [ ] 6-40 words; one idea.
- [ ] No promo, links, hashtags or tagging the creator's own account.
- [ ] Facts about the creator only from the profile / verified facts.
- [ ] Scored with `--post`; nothing under 70 or with a dealbreaker.

## Errors and edge cases

- No post text, only a link: ask the creator to paste the caption or describe the reel. You do not open Instagram.
- Sensitive post (grief, illness, tragedy): one sincere, simple line; no advice, no questions, no brand voice.
- Controversial topic outside the creator's niche: suggest not commenting.
- Post in another language: comment in that language only if the creator speaks it.

## Examples

Post: "Stop feeding your starter at midnight. It peaks while you sleep."

Good (`examples/good-comment.txt`, comment score 95 with `--post examples/post.txt`):
`The midnight-feed thing matched what I saw too. Did you find it changes in winter, when the kitchen runs colder?`

Bad (`examples/bad-comment.txt`): `Great post!! 🔥🔥 check out my page for more baking tips` → generic, self-promo and spam-marker dealbreakers (capped at 10).
`🔥🔥🔥` (`examples/emoji-comment.txt`) → generic, 12.5.

## References

- `references/comment-styles.md`: nine styles with templates and when to use each.
