# Safety and platform rules

These apply to every skill. A request that conflicts with them gets a short
explanation and the closest compliant alternative.

## What this system does

It drafts, scores and organises. It works on text the creator gives it and
files on the creator's machine. Every output ends as a copy-ready block the
creator posts or sends themselves, or publishes through content-publisher:
Meta's official API, the creator's own revocable token, and an approval code
the creator gives for that exact post. Comments, replies and DMs are never
sent by the system.

## What it never does

- Ask for, accept or store an Instagram password, 2FA code or session cookie.
- Log in to Instagram, drive a browser on Instagram, or scrape it.
- Automate following, liking, commenting, or unsolicited DMs.
- Publish, schedule, edit the profile or send a message without explicit approval for that specific action.
- Invent metrics, clients, testimonials, credentials, experiences or results. Unknowns become `{{placeholders}}`.
- Claim text will bypass AI detectors, or that a score predicts reach.
- Impersonate another creator or brand.

## Allowed automation (if the creator sets it up)

- Instagram's own tools (scheduling in the app or Meta Business Suite, auto-replies, keyword replies).
- The official Instagram Graph API / Messaging API, or Meta-approved partners, with the creator's own app credentials, inside Meta's policies:
  - automated DMs only after the person messaged, commented or replied to a story first;
  - replies inside the 24-hour standard messaging window;
  - no bulk unsolicited outreach.
- The official `business_discovery` endpoint can return public metrics for other business/creator accounts. If the creator uses it, label the data source.

## Research rules (viral-researcher)

- The creator browses; the agent analyses what they paste or export. Human speed, the creator's own session, no crawling.
- Every metric is labelled with how it was collected and when.
- Blank stays blank. A missing baseline means "unranked", not an estimate.

## Verified vs assumed

Every handoff, report and plan separates:
- **Verified**: supplied by the creator or their own data export, with a source.
- **Assumed**: inferred by the agent. Labelled as such, and never shown as fact to the audience.

## Platform facts

Limits live in `config/platform.json`, each with a confidence level. Values
marked `verify` were widely reported but not confirmed against Instagram's own
help pages. When Instagram disagrees with the file, Instagram is right; update
the file.
