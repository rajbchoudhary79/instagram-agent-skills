---
name: dm-assistant
description: >-
  Write Instagram DMs that respect the person and the platform: keyword
  delivery messages, replies to story responses and inbound leads, personal
  first messages to people who engaged, collaboration proposals, and at most
  two lead follow-ups, all personalised, checked for pressure and spam
  patterns, and within Instagram's messaging rules. Use when the user says
  "write a DM", "reply to this DM", "collab pitch", "follow up with this
  lead", "keyword auto-reply message", or "what do I send people who comment
  WORD".
---

# dm-assistant

Paths are relative to this skill's folder. Shared tools: `python3 scripts/core.py ...`.

## When to use

- Someone messaged, replied to a story, commented a keyword, or asked about the offer.
- The creator wants to pitch a collaboration to one specific person they follow and engage with.
- A conversation went quiet and needs one of (at most) two follow-ups.

Never for: bulk outreach, cold automated messages, buying or scraping lists.

## Inputs

### Required
- The kind of message: keyword, first, reply, lead, collab, followup.
- The context: their message / comment / story reply, or (for collabs) their post and why they are a fit.

### Optional
- Conversation history; which follow-up this is; hours since their last message; whether it will be sent by an automation tool.
- What the keyword delivers and the link (profile `goals.cta`).

## Workflow

1. **Profile.** `python3 scripts/core.py profile show`: voice, offer, CTA keyword and delivery, verified facts.
2. **Check it is allowed** (`references/dm-policy.md`): did they message or engage first? Is this follow-up #3? Is an automation tool involved, and are we inside 24 hours of their last message? If not allowed, say so and stop.
3. **Template.** `python3 scripts/dm.py templates` and pick the skeleton. Skeletons are structure only; write the message for this person.
4. **Write it.** Reference their exact words or work. One reason, one easy question. Short enough to read in the preview. No links in first/collab/followup messages unless they asked. Facts only from the profile.
5. **Check.** Save and run `python3 scripts/dm.py lint draft.txt --kind <kind> --post context.txt [--followup N] [--automated --they-messaged-first --hours-since H]`. Fix every FAIL and WARN.
6. **Humanize** (content-humanizer), then deliver. The creator sends it. For keyword automation, the creator pastes the message into Instagram's own tools or an approved partner.

## Decisions

- **Keyword delivery:** deliver first, then one question about how they will use it. No upsell in the first message.
- **Inbound lead:** answer their question directly, then one qualifying question. Price if the creator shares it publicly.
- **Collab pitch:** lead with something specific of theirs, then the idea in one sentence and why it helps *their* audience. Make "no" easy.
- **Follow-ups:** each one adds something new (a resource, an answer, an update); never "just bumping this". Two maximum, then stop.
- **Story replies:** react to what they said; it is a conversation, not a funnel step.

## Output format

```
DM  (<kind>)  to @<handle>

<message, exactly as it would be sent>

WHY: references <their detail>; one question; no link (they haven't asked yet)
CHECKS: dm.py <verdict> · dm quality <score> · policy ok (they messaged first / manual send)
NEXT: if no reply in 3-4 days -> follow-up 1 (adds: <what new value>)
```

## Quality checklist

- [ ] Allowed: they engaged first, or a manual, one-to-one, personalised collab pitch.
- [ ] References something specific from them.
- [ ] One question; no pressure, fake urgency or bait.
- [ ] No unfilled `{{placeholders}}`; facts only from the profile.
- [ ] Follow-up count ≤ 2.
- [ ] Automation only for keyword deliveries, only through official tools, inside the 24 h window.
- [ ] dm.py lint passed; nothing sent by the agent.

## Errors and edge cases

- `FAIL automation`: an automated message to someone who has not engaged. Not allowed; make it a manual personal message or drop it.
- `FAIL window`: over 24 h since their last message for an automated send. Send manually (personal) or not at all.
- `FAIL followups`: third follow-up. Stop; suggest leaving the door open in the last message.
- `REFUSED` from `dm.py render`: slots missing; fill them with real details, never generic filler.
- The person asked to stop: no more messages. Note it.
- Requests for login codes, passwords or payments outside official channels: never write those messages.

## Examples

Good collab (`examples/good-collab.txt`, with `--post examples/their-post.txt`): references their discovery-call reel, one-sentence idea, why their audience benefits, easy no → READY, DM quality 100.

Bad (`examples/bad-collab.txt`): "I came across your profile and you'd be perfect... Only a few spots left... www.mysite.com", sent by automation → BLOCKED (automation without consent, spam marker, pressure phrases, link).

## References

- `references/dm-policy.md`: what Instagram allows, the 24-hour window, follow-up rules.
- `templates.json`: skeletons with triggers.
