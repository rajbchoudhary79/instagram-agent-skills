---
name: reply-assistant
description: >-
  Work through the comments under the creator's own posts: triage them into
  leads, support issues, keyword requests, questions, pushback, stories,
  praise, tags and spam, put them in reply order, and draft context-aware
  replies in the creator's voice that move the right conversations to DMs.
  Use when the user says "reply to my comments", "help with my comments",
  "what do I say to this comment", "someone asked the price in the comments",
  "deal with a negative comment", or pastes comments from their post.
---

# reply-assistant

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- After posting (the first hour matters for the conversation, not just reach).
- A backlog of comments, or a single tricky one (a lead, a complaint, a troll).

Not for: comments on other people's posts (comment-assistant), DMs (dm-assistant).

## Inputs

### Required
- The comments, pasted or exported: `username: comment` per line, or CSV with username/text (likes optional).
- What the post was about (caption or a one-line summary).

### Optional
- The post's comment keyword (default: profile `goals.cta.keyword`).
- Known context about a commenter (client, repeat commenter).

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: voice, offer, CTA keyword and delivery, disclaimers.
2. **Triage.** `python3 scripts/triage.py comments.txt [--keyword WORD]`. Read every comment yourself; correct any category the rules got wrong (`references/reply-playbook.md`).
3. **Order.** Lead → support → keyword → question → pushback → story → praise / general. Spam is hidden or deleted, never answered.
4. **Draft replies** for each category using the playbook. Reply to what they actually said. Keep it short; one idea; the creator's voice. Facts only from the profile.
5. **Move to DM** when it is a lead, a support problem or anything personal: reply publicly ("Sent you a DM") and draft the DM with dm-assistant. Keyword requests get the delivery via the creator's DM process (manual or official automation), plus a short public reply.
6. **Patterns.** 3+ similar questions → suggest a reply reel or carousel (hand off to reel-creator). Repeated objection → note it for content-planner.
7. **Check.** Gate the batch: `python3 scripts/core.py gate replies.txt --type reply`. Nothing is posted by you.

## Decisions

- **Pushback:** one reply with substance, or none. Thank them for the specific point, answer it, stop. Never argue twice; never mock.
- **Trolls and abuse:** do not reply; suggest hide, restrict or block. Escalate threats to the platform's reporting.
- **Price in public:** follow the creator's preference; default to answering briefly if the price is public, otherwise inviting to DM.
- **Praise:** short and specific ("Glad the one-page bit helped"), or just a like for emoji-only praise.
- **Tags:** like it; reply only if they added words.

## Output format

```
REPLY QUEUE  <n> comments  (lead 1, support 1, keyword 2, question 3, ...)

1. [lead]    @jonny_k: "How much is the weeknight sourdough guide?"
   reply:    "It's in my bio, and I just sent you a DM with what's included."
   then:     DM via dm-assistant (inbound_lead_reply)
2. [support] @kim.creates: "didn't get the download link"
   reply:    "Sorry about that, sending it to you in DMs now."
...
SPAM: hide @promo_king99 (promotion offer)
PATTERNS: 3 people asked about cold kitchens -> reply reel idea
```

## Quality checklist

- [ ] Every comment read, not just triaged.
- [ ] Leads and support first; spam not replied to.
- [ ] Replies answer what was said, in the creator's voice, briefly.
- [ ] No promises, prices or results beyond the profile.
- [ ] DM handoffs drafted with dm-assistant where needed.
- [ ] Gate run; nothing posted by the agent.

## Errors and edge cases

- Comments without usernames: triage still works; replies address the content.
- Mixed languages: reply in the commenter's language if the creator speaks it; otherwise suggest a short reply in the creator's language.
- A comment reveals personal or sensitive information: suggest hiding it and moving to DMs.
- A complaint that may be legal or medical: acknowledge, move to DM, flag for the creator. No admissions or advice in public.

## Examples

`examples/comments.txt` (10 comments, keyword STARTER):
```
lead 100      @jonny_k       How much is the weeknight sourdough guide?
support 90    @kim.creates   I bought the guide but didn't get the download link
keyword 85    @maria.bakes   STARTER
question 70   @lee.makes     what if my kitchen is really cold though?
pushback 65   @tara_loaves   Disagree, feeding at night works great for my rye starter
story 55      @crumb.nine    This happened to me last week...
praise 30     @ben, @olu     tag 20  @sam_p @jo.bakes     spam 0  @promo_king99
```
Good pushback reply: "Fair point on rye. It ferments faster, so a night feed can work there. This was about wheat starters."
Bad: "Agree to disagree 🙃" or arguing a second time.

## References

- `references/reply-playbook.md`: per-category reply shapes and examples.
- `categories.json`: triage rules (edit to fit the niche).
