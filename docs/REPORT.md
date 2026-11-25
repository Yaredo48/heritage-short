# The Silent Language of a Mother's Love — Report

**B2W0 · AI-Content Generation · Assignment 1: Codebase and Report**

| | |
|---|---|
| Repository | https://github.com/Yaredo48/heritage-short |
| One command | `make setup && make film` (README.md, "Install" and "Run it") |
| Film (9:16 / 16:9) | ✍️ _link_ / ✍️ _link_ |
| Walkthrough | ✍️ _link_ |
| Public post | ✍️ _link_ |

> **Before you export this file:** replace every ✍️ with your own words and real events, delete this box, then run `make report`. That writes `docs/REPORT.pdf` and `docs/REPORT.docx`. Everything not marked ✍️ is backed by a file named in brackets. Check each one, and change anything you would not say yourself. The interviewer will ask about it.

---

## 1. What I set out to make, and for whom

I set out to make a 60–90 second film about my mother. She grew up in Yeki Woreda, Sheka Zone, where life was hard and chances were few. She gave up her time, her comfort and many of her own dreams so her children could have what she never had.

**Who it is for.** My family: my mother, my siblings, and our relatives in Ethiopia and abroad. They will watch it on their phones, in a vertical format, in our family Telegram group. At the end they should recognise that her love showed less in what she said than in what she gave and endured. I wrote this before generating anything (DESIGN.md §1, commit `1b715f8`).

**What it is.** Nine shots and about 84 seconds, in two versions: vertical (9:16) and horizontal (16:9).
- Amharic narration from a stock Gemini TTS voice ("Charon"), not a copy of anyone's voice.
- English subtitles.
- Original instrumental music, turned down under the voice.
- An end card saying the film was made with AI.
- One recurring object, her old coffee cup, which opens and closes the film.

Her face is never shown until she consents. She appears from behind, through her hands and through the cup (ETHICS.md, DESIGN.md §3).

**How it is built.** One validated file, `storyboard.json`, feeds five stages:
1. keyframes (FLUX.2 klein on Cloudflare)
2. moving shots (Wan 2.2 on Kaggle, with an FFmpeg pan-and-zoom fallback)
3. music (ACE-Step 1.5 on Kaggle)
4. narration (Gemini TTS)
5. assembly (FFmpeg)

Every model output is cached by a hash of its inputs, retries follow the provider's own wait hint, and every model call writes one line to `runs.jsonl`. `make film` rebuilds everything. A fresh clone with no API keys rebuilt the film with 0 model calls and 18 cache hits (COSTS.md, "Local compute"; ARCHITECTURE.md).

## 2. What I learned from my audience ✍️

> Fill this from DESIGN.md §4 and §5 **after** the tests. Each test needs at least three people from the audience above. Quote what they actually said.

**First test: the radio cut** (`outputs/radio/radio_cut.mp4`, Amharic narration over the temp score on a black screen).
- Who, when and how: ✍️
- What they said, in their words: ✍️
- What surprised me: ✍️
- What I changed in `storyboard.json` (version 2, changelog line): ✍️

**Second test: the near-final cut**, watched on a phone.
- Who (at least one person who did not hear the radio cut): ✍️
- What they said: ✍️
- What changed (version 3, changelog line): ✍️

**Before the tests, the evidence had already changed the story** (DESIGN.md §6):
- **The narration sets the timing.** The Amharic lines run longer than planned, so the 70 seconds of planned shots grew to 81.4 seconds (`make timing`).
- **Faces stay hidden until consent.** This began as a consent rule and became a creative choice: hands and the cup carry the story.

## 3. The hardest problem, and how I solved it

**The narration did not fit the film, and the free TTS quota made retakes almost impossible.** ✍️ _Confirm this was the hardest for you, or replace it._

1. **The problem.** The first full Amharic take was 77.4 s of speech, which made the film 92.2 s, over the 90-second limit (`make timing`; FAILURES.md F05). The cause was my style instruction, "gentle pauses between phrases". The model put 0.5–1.1 s of silence between phrases; in shot s02 alone there were four pauses of 0.63–1.13 s.
2. **The obvious fix ran into the quota.** I tried a retake with a faster style, but the Gemini TTS free tier allows 3 requests per minute and about 10 per day, and nine lines need nine calls. The retake stopped after 3 lines. Those 3 lines were only 12 % shorter overall, and one (s03) came out *longer*, so the voice style is not a reliable control (E02, F03, F04).
3. **The standard tool was not enough.** FFmpeg's `silenceremove` only took the total from 77.4 s to 75.3 s (E03).
4. **What worked.** I wrote a pause compressor in about 60 lines of standard Python (`pipeline/audio.py`). It cuts any silence longer than a set limit down to that limit.
   - I compared three limits: 0.35, 0.45 and 0.55 s (E04).
   - At 0.45 s the narration went from 77.4 s to 67.9 s, and the film from 92.2 s to **84.4 s**.
   - It needed **zero extra model calls**.
   - The original takes are kept untouched in `outputs/narration/raw/`.
   - The limit is one number in the storyboard (`voice.max_pause_s`) and is part of the cache key, so changing it regenerates only the trimmed audio, never the TTS call.
5. **What it fixed in the retry logic.** The old backoff waited 2–4 s when the server asked for 39 s. Then it spent about 10 minutes retrying a daily quota that would only reset 17 hours later. Retries now read the server's wait hint and stop at once when the wait is over 2 minutes, with a clear "quota exhausted, rerun later" message (`pipeline/common.py`; `tests/test_pipeline.py::test_daily_quota_fails_fast`).

**What it taught me:** on a free tier the quota is the real budget. A deterministic fix after generation, cached and tested, beats paying for more generation. It is also why family corrections to the Amharic have to be gathered and applied in one batch (COSTS.md).

## 4. A suggested practice that beat my instinct

**Logging every model call to `runs.jsonl`.** ✍️ _My instinct was to …_ (for example, "print errors to the terminal and move on"). _Replace it with what you would really have done._

The log is the evidence behind most of this report:
- **It showed the smoke test had never run.** The smoke-test output files were in the repo, but they were 0 bytes and there was no `runs.jsonl`. The files existed; the log showed that nothing had run (F01).
- **It separated two different limits.** The 429 errors looked the same, but their bodies said "3 requests per minute, retry in 39s" and "10 requests per day, retry in 17h50m8s". Only the log told me the burst limit from the daily quota, which is why the retry logic now treats them differently (F03, F04).
- **It became the cost report.** `make costs` builds the COSTS.md table straight from the log: every line has stage, model, status, latency and attempt.
- **It proves the cache works.** A run where nothing changed adds `cache_hit` lines and no `model_call` lines; the clean-clone run added 0 model calls and 18 cache hits. The walkthrough shows the same thing live for one changed shot.

## 5. A suggested practice that did not work as expected

**"Make a reference sheet first, then condition every keyframe on it."**

- **What I tried.** I made four style-sheet candidates (seeds 201–204) and chose 201. I then regenerated shots s02 and s05 with the sheet as the reference image, keeping the same prompts and seeds, and compared them with the versions made without it (E07, F08).
- **Result: worse.** FLUX.2 klein treats an input image as content to edit, not as a style to borrow.
  - In s02, it pasted the sheet's table, coffee pot and cup into the middle of the Sheka forest.
  - In s05, the cream-and-green dress and the oil lamp disappeared, and a child's face appeared that was not in the prompt.
- **What I did instead.** I set `use_style_reference: false`. A shared text style block appended to every prompt kept the look consistent across the nine shots.

**What I take from it:** a practice that works with one model can fail with another, and the only way to know is a side-by-side comparison with the seed fixed. ✍️ _Add your own view._ The character reference sheet is still untested, because it would show her face and consent is pending.

## 6. Beyond the floor ✍️

> The brief judges this on insight, not volume. Keep what is true, and add any extra work you do before submitting.

- **A consent gate in code, not only in a document.**
  - While `consent.likeness_approved` is false, shots that show her use a no-face prompt, no character sheet is ever generated, and the Wan prompts ask for her face to stay hidden.
  - The validator refuses to set the flag to true while ETHICS.md still says *Pending*.
  - Until the script is approved, both exports carry a DRAFT mark.
  - It is tested, and each time the gate applies it writes a `consent_gate` line to `runs.jsonl` (6 so far).
  - One "no face" prompt still showed her profile, which is why I now check every character keyframe by eye (E05, F07).
- **Measured audio, not only listened to** (E09, E10).
  - Ducking: the music drops by 13 dB under speech and is unchanged in the pauses.
  - Loudness: the target holds after AAC encoding, at −14.04 LUFS and −1.76 dBTP.
- **Amharic and the image model** (E01, E06). The model does not know "jebena" and drew a vase, so objects are described by their shape. ✍️ _If you collect your listeners' pronunciation notes (DESIGN.md §4, last column), add here exactly which words the Amharic TTS got wrong. That is the "extra language tested, document where it fails" direction from the brief._
- **An offline end-to-end test.** Fake models and real FFmpeg build both exports, then check they are 60–90 s long, the right size, and have audio and subtitles (`tests/`, 23 tests).
- ✍️ _Anything else you finish, e.g. a blind preference test of a Wan clip against the pan-and-zoom shot (EXPERIMENTS.md E12)._

## 7. What I would build next ✍️

> Choose one or two and say why. Ideas that follow from this project:

- Several TTS takes per line, compared blind by Amharic speakers, so the voice is chosen by ear rather than by length.
- A small LoRA trained on a character sheet once she consents, then a measurement of whether her likeness stays more consistent across shots.
- A simple form where a relative who does not code tells their own story and gets a `storyboard.json`, then a film, back.

---

## Appendix: where the evidence is

| Claim | Evidence |
|---|---|
| Audience and intent were written before generation | DESIGN.md §1; commit `1b715f8` |
| Every shot has a stated reason | DESIGN.md §3; `reason` field of every shot in `storyboard.json` |
| The storyboard is validated before every stage | `schema/storyboard.schema.json`; `pipeline/validate.py`; `tests/test_storyboard.py` |
| Only what changed regenerates | `cache_hit` vs `model_call` lines in `runs.jsonl`; `tests/test_pipeline.py` (cache tests) |
| Retries and quota handling | `pipeline/common.py`; FAILURES.md F02–F04 |
| One command from a clean clone | COSTS.md, "Local compute" (fresh clone, exit 0, 0 model calls) |
| Ten experiments, each with a hypothesis | EXPERIMENTS.md E01–E10 |
| Real blockers and fixes | FAILURES.md F01–F09 |
| Latency, cost and free-tier limits | COSTS.md (generated from `runs.jsonl`) |
| Consent, licences, labelling | ETHICS.md; `consent` block in `storyboard.json` |
| Both exports verified | `outputs/final/report.json` (duration, size, codecs, LUFS, true peak) |
