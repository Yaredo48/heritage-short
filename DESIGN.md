# DESIGN

## 1. Audience, intent and story notes

_Written on 25 Nov 2026, before anything was generated (commit 1b715f8)._

### A. Audience

- **Who will watch:** My mother, siblings, relatives, and future generations of our family, including relatives living in Ethiopia and abroad.
- **Where they will watch:** Primarily on smartphones, in a vertical video format, shared through our family Telegram group.
- **What they should feel or understand at the end:** They should recognize and appreciate the sacrifices, resilience, and unconditional love of a mother, understanding that the greatest expressions of love are often demonstrated through years of dedication and sacrifice.

### B. Intent

- **Purpose:** To create an emotionally meaningful cinematic tribute celebrating my mother's life, sacrifices, resilience, and lasting influence on our family.
- **Design question:** How might we tell my mother's authentic life story through cinematic storytelling, emotional narration, and meaningful visual symbolism so that her sacrifices and unconditional love remain unforgettable to our family and future generations?
- **Creative direction:** A combination of authentic documentary storytelling and cinematic visual representation.
- **Constraints:** 60–90 seconds, Amharic narration, English subtitles, free tools only, and a six-hour production timeframe.

### C. Story Notes

1. My mother grew up in Yeki Woreda, Sheka Zone, in the Southwest Region of Ethiopia, where life was difficult and opportunities were limited.
2. Despite the challenges surrounding her, she became a hardworking, caring, and determined woman who believed that her children's future was more important than her own comfort.
3. When she took on the responsibility of raising her children, she encountered difficulties that tested her strength, patience, and determination.
4. Throughout her journey, she sacrificed her time, personal comfort, and many of her own dreams to give her children opportunities that she herself had never experienced.
5. Her love was not simply expressed through words; it was demonstrated through countless acts of care, perseverance, and sacrifice that shaped the lives of her children.
6. Today, her journey reminds our family that a mother's love is measured not only by what she says but also by what she gives, endures, and does for the people she loves.
7. Every morning, her old coffee cup tells a quiet story. It symbolizes her patience, consistency, warmth, and the countless ordinary moments through which she made our home feel like home.
8. Although time passes, the values she taught us and the sacrifices she made remain part of our family's identity and will continue to inspire future generations.

## 2. Story shape

Logline: A child of Sheka tells how their mother gave up her own comfort and dreams so her children could have the chances she never had, a love remembered every morning through her old coffee cup.

The film opens and closes on the same object, her old coffee cup. In between it moves from where she came from (Sheka), to what she gave (work, sleepless nights, her own dreams), to what it bought (her children's chances), to what remains (a family around her cup). The narrator is her grown child. The words come only from my own story notes; nothing about her life was invented for the film.

## 3. Why each shot exists

| Shot | Size | Narration (English) | Reason |
|---|---|---|---|
| s01 | extreme close-up | Every morning, my mother's old coffee cup tells us a quiet story. | Opens on the motif, the old coffee cup, so the ending can return to it; a quiet, intimate first feeling. |
| s02 | extreme wide | She grew up in Yeki, in Sheka Zone, where life was hard and chances were few. | Establishes where she came from: the green forests of Sheka, beautiful but hard. |
| s03 | wide | Despite the hardship around her, she grew into a hardworking, caring and determined woman. | Her childhood shown without a face: a girl carrying water alone, so we feel the hardship that shaped her. |
| s04 | medium | When she took on raising her children, hardship tested her strength, patience and resolve. | Introduces her as a mother at work before dawn; the responsibility that tested her. |
| s05 | close-up | She gave up her time, her comfort and many of her own dreams, | Sacrifice shown through action, not words: tired hands working late at night for her children. |
| s06 | wide | so that we could have the chances she never had. | What her sacrifice bought: her children walking to school, toward the chances she never had. |
| s07 | medium close-up | Her love was not only spoken; it showed in countless acts of care, endurance and sacrifice. | Love shown in everyday care: the family coffee ceremony she held together, warm and close. |
| s08 | close-up | Today we know: a mother's love is measured not only by what she says, but by what she gives, endures and does. | Present day: older hands hold the same cup; the motif returns and links her past to our present. |
| s09 | wide | Time passes, but her values and her sacrifice remain our family's identity, for the generations to come. | Closing image of legacy: hands of every generation sharing coffee around her cup; the feeling we want to leave. |

Shot sizes move from extreme close-up (the motif) to extreme wide (the place) and back to close-ups of hands for feeling. Until consent is recorded her face never appears: she is shown from behind, through her hands, and through the cup (see ETHICS.md).

## 4. First user test: the radio cut

**Prototype:** `outputs/radio/radio_cut.mp4`, made by `make radio`: Amharic narration over the temp score on a black screen, with English subtitles, 84 s.
**Who:** at least three people from the audience in section 1 (family members, Amharic speakers; one diaspora relative if possible).
**How:** play it once without explanation, then ask:
1. In one sentence, what is this film about?
2. What did you feel at the end?
3. Which line or moment stayed with you? Which one lost you?
4. (Amharic speakers) Was any word or name mispronounced? Did the voice sound natural and warm?
5. Is anything in it not true to her, or something she would not want said?

**Status at submission (26 Nov 2026): not conducted.** The radio cut, the questions above and ready-to-send messages (`docs/FAMILY_KIT.md`) are prepared, but no viewer has watched it yet, so there are no answers to record. No change in `storyboard.json` is attributed to audience feedback, and the storyboard is still version 1.

When the test is run, record one row per person here (relation, where they watch, date and how, what they said in their own words, pronunciation notes). Then change the storyboard, set `version: 2`, and add a changelog line that names the feedback behind each change.

## 5. Second user test: the near-final cut

**Prototype:** `outputs/final/..._vertical.mp4`, watched on a phone (the real viewing condition).
**Who:** at least three people from the audience; at least one who did not see the radio cut.
**Ask:** the same questions, plus: Did the pictures match the words? Did any image feel wrong for our family or for Sheka? Could you read the subtitles?

**Status at submission (26 Nov 2026): not conducted**, for the same reason as test 1. The near-final cut exists (`outputs/final/*_vertical.mp4`, verified in `report.json`), but it has not been shown to viewers.

## 6. Automated checks that stand in for some test questions (not audience evidence)

These measurements answer, by machine, some of the questions the user tests would ask a person. They are **not** a substitute for viewers: they say nothing about whether the story lands or feels true to her.

| Test question | Automated check | Result |
|---|---|---|
| "Could you read the subtitles?" | Reading speed of every cue (E15) | max 13.8 characters/s, shortest cue 3.3 s: inside common guidance |
| "Was the music too loud under the voice?" | Music level under speech vs in pauses (E10) | −13 dB under speech, unchanged in pauses |
| "Was it too quiet or too loud overall?" | Integrated loudness and true peak of both exports (E09, `report.json`) | −14.04 LUFS, −1.76 dBTP |
| "Was any Amharic word mispronounced?" | ASR round trip of the 9 narration lines (E16) | mean CER 0.123 with homophones folded; four meaning-changing words flagged (s01 በየማለዳው, s02 እናቴ ያደገችው, s03 ችግር ቢኖርም, s05 ሠዋች), to play to a native speaker first |

## 7. Decisions already driven by evidence (before user tests)

- Narration first, pictures second: the TTS takes set each shot's length (`make timing`), and the planned 70 s of shots became 81.4 s because the Amharic lines run longer than planned (EXPERIMENTS.md E02–E04).
- Faces hidden until consent (ETHICS.md). This is now also a creative choice: hands and the cup carry the story.
- "Jebena" and "sini" are not understood by the image model, so the objects are described by shape (E01, E06).
