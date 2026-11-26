# Family kit: consent and the two audience tests

These are the only parts of the project that cannot be done in code: they need your mother and your family. Each one is set up below so that it takes minutes. When you have the answers, paste them to Claude exactly as people wrote them, and they will be written into DESIGN.md and ETHICS.md and turned into storyboard changes.

**Do not invent or "tidy up" answers.** The brief scores real audience evidence. The interview will ask you what people said. A missing test, stated honestly, costs less than a made-up one.

---

## 1. Consent from your mother: done (26 Nov 2026, recorded in ETHICS.md)

The steps below are kept for reference, or in case anything changes.

**Send or show her:**
- `outputs/radio/radio_cut.mp4` (1.9 MB): the narration she would hear.
- One vertical film frame: open `outputs/final/the_silent_language_of_a_mother_s_love_vertical.mp4` on your phone. The DRAFT mark is expected.

**Explain in your own words, in Amharic:**
1. The film is about her life, from your story notes, for the family Telegram group and a public post marked "made with AI".
2. The pictures are made by an AI model. They are not photographs of her. The woman in the film is seen only from behind or by her hands.
3. The voice is a computer voice, not hers and not a copy of hers.
4. Read her every Amharic narration line (`storyboard.json → shots[].narration.am`), or let her hear the radio cut, and ask whether every sentence is true and something she is happy to have said about her.
5. She can say no, ask for changes, or ask for it to be taken down later.

**Ask her two separate questions:**
- **A.** "May I share this film, with these words, made this way?" This is `script_approved`.
- **B.** "May the AI also make a picture of a woman's face representing you?" This is `likeness_approved`. You do not need B. The no-face film is complete.

**Then give Claude:** the date, how you asked (in person, phone call, voice note), her answer to A and to B, and any changes she asked for. Claude will fill the row in ETHICS.md §1 using the sentence already prepared there, and set the flags. Keep a voice note or a message from her as your own record. Do not commit private recordings to the repository.

---

## 2. User test 1: the radio cut (at least 3 people)

**File to send:** `outputs/radio/radio_cut.mp4` (1.9 MB): Amharic narration with English subtitles over the temp music, on a black screen.

**Message to paste into Telegram** (send it to each person separately, so they don't influence each other):

> Hi! I'm making a short film about Emaye for a course. Could you watch this 84-second draft (sound on) and answer 5 quick questions? Honest answers help me most.
> 1. In one sentence, what is this film about?
> 2. What did you feel at the end?
> 3. Which line or moment stayed with you, and which one lost you?
> 4. Was any Amharic word or name mispronounced? Did the voice sound natural and warm?
> 5. Is anything in it not true to her, or something she would not want said?

(Translate the message into Amharic if that suits them better. "Emaye" is a placeholder: use whatever the family calls her.)

**Collect for each person:** their relation to you (sister, uncle…), where they live or watch, the date, and their answers word for word. Screenshots are fine.

---

## 3. User test 2: the near-final cut (at least 3 people, at least one who did not do test 1)

Run this **after** test-1 changes are applied and, ideally, after the ACE-Step music is imported, so they watch the near-final version.

**File to send:** `outputs/final/the_silent_language_of_a_mother_s_love_vertical.mp4` (28 MB). People must watch it **on a phone**: that is the real viewing condition.

**Message:**

> Here is the nearly finished version (84 s, sound on, on your phone please). Same questions as before, plus three:
> 6. Did the pictures match the words? Did any picture feel wrong for our family or for Sheka?
> 7. Could you read the subtitles comfortably?
> 8. Was the music too loud, too quiet, or right under the voice?

---

## 4. What happens with the answers

Paste every answer to Claude. Claude will then:
1. Fill in DESIGN.md §4 and §5, quoting people exactly, with one row per person.
2. Turn the agreed changes into `storyboard.json` edits: version 2 after test 1, version 3 after test 2, each with a changelog line that names the feedback behind it.
3. Re-run only what changed. A changed Amharic line costs one TTS call, and about 10 are free per day, so changes are batched. Then run `make film`.
4. Update report §2 from the real answers. You confirm the wording.
