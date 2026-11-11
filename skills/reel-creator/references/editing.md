# Visuals, edits and on-screen text

## Frame and safe zones

- 1080 x 1920 (9:16). Keep text out of the bottom ~20% (caption, buttons) and top ~14% (account, audio).
- The grid shows a 3:4 crop of the cover. Choose a cover frame with the headline centred.

## On-screen text

- The hook gets on-screen text, every time. Many viewers start muted.
- Text is a compressed version of the line, not a transcript: 3-7 words.
- Viewers read ~3-4 words per second; script_timer.py flags text that cannot be read in the time it is up.
- One text block on screen at a time. High contrast, consistent position.
- Burned-in captions (full transcript) are separate from emphasis text; if both are used, keep emphasis text above the captions.

## Visual change cadence

- Something changes every 2-4 seconds: a cut, a zoom, b-roll, a prop, a screen.
- script_timer.py flags beats longer than 6 s with no visual or edit note.
- Talking head: alternate wide/punch-in (jump-cut zoom) to reset attention without b-roll.

## Edit vocabulary (use in [edit: ...] or [cut]/[zoom] notes)

| note | what it means | use for |
| --- | --- | --- |
| cut | hard cut to next shot | default |
| jump cut | same framing, time removed | trimming pauses in talking head |
| zoom / punch-in | crop in 10-20% | emphasis on a key line |
| match cut | similar shape/motion across two shots | before/after, transitions with a prop |
| whip | fast pan blur between shots | energy shift, list items |
| speed ramp | slow then fast (or reverse) | demos, reveals |
| text pop | on-screen text appears on the word | numbers, keywords |
| sfx | small sound on a cut or text pop | emphasis; keep subtle |
| b-roll | cutaway footage over voice | anything you mention that can be shown |

## B-roll list prompts

For each beat, ask: can the noun in this line be shown? (the jar, the
dough, the oven, the counter, the before/after). Write the list as shots to
capture in one session.

## Audio

- Voice first. Music, if any, sits well under the voice.
- Describe the type of track ("low, steady instrumental"). Do not claim a specific song is trending; the creator checks the app's trending audio.

## Filming checklist (include in the reel output)

- Setting from `visual.settings`, light facing the creator.
- Framing: eyes on the upper third; space above the head for text.
- Props list from the script nouns.
- Record the hook three ways (different energy) and pick in the edit.
- Record 3-5 seconds of silent b-roll per beat that has a visual note.
