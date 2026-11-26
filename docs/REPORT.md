# The Silent Language of a Mother's Love — Report

**B2W0 · AI-Content Generation · Assignment 1: Codebase and Report**

| Item | Where |
|---|---|
| Repository | https://github.com/Yaredo48/heritage-short |
| One command | `make setup && make film` (README.md, "Install" and "Run it") |
| Film, walkthrough, post | Submitted with assignment 2. The film is shared privately with the graders and not posted publicly, because my mother's consent (26 Nov) covers the assignment and its private evaluation only (ETHICS.md) |


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

## 2. What I learned from my audience

**The honest answer: the two audience tests were not run before the deadline.** The radio cut (`outputs/radio/radio_cut.mp4`), the near-final cut, the five test questions and ready-to-send messages are all prepared (DESIGN.md §4–§5, `docs/FAMILY_KIT.md`), but no family member has watched either cut yet. I am not reporting reactions I do not have. As a result:
- no change in `storyboard.json` is attributed to audience feedback (it is still version 1);
- three questionnaires (comprehension, emotional engagement, technical quality) are prepared in DESIGN.md §5 but have no answers yet.

My mother's written consent was recorded on 26 Nov (ETHICS.md). It covers the assignment and its private evaluation, so the film is shared privately, not posted publicly.

**What I did instead, clearly labelled as not audience evidence** (DESIGN.md §6): I answered by measurement the test questions a machine can answer.
- *Could you read the subtitles?* At most 13.8 characters per second, with the shortest cue 3.3 s (E15).
- *Is the music too loud under the voice?* It is 13 dB lower under speech (E10).
- *Was any Amharic word mispronounced?* An ASR round trip of all 9 lines (E16) flags four specific words, in s01, s02, s03 and s05. Those are exactly the words to play to a native speaker first.

These checks cannot tell me whether the story lands or feels true to her. Only the family can.

**Before the tests, the evidence had already changed the story** (DESIGN.md §6):
- **The narration sets the timing.** The Amharic lines run longer than planned, so the 70 seconds of planned shots grew to 81.4 seconds (`make timing`).
- **Faces stay hidden until consent.** This began as a consent rule and became a creative choice: hands and the cup carry the story.

## 3. The hardest problem, and how I solved it

**The narration did not fit the film, and the free TTS quota made retakes almost impossible.**

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

**Logging every model call to `runs.jsonl`.** The default when a script calls an API is to print errors to the terminal and move on. Writing one JSON line per attempt looks like overhead at first; it turned out to be the evidence behind most of this report:

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

**What I take from it:** a practice that works with one model can fail with another, and the only way to know is a side-by-side comparison with the seed fixed. The suggestion assumes a model that borrows style from a reference; FLUX.2 klein instead edits whatever image it is given. The character reference sheet is still untested, because it would show her face and consent is pending.

## 6. Beyond the floor

The brief judges this part on insight, not volume. Each item below exists in the repository and was measured or tested.

- **A consent gate in code, not only in a document.**
  - While `consent.likeness_approved` is false, shots that show her use a no-face prompt, no character sheet is ever generated, and the Wan prompts ask for her face to stay hidden. The Wan notebook also leaves her shots out by default, because image-to-video could turn her face to the camera.
  - The validator refuses to set the flag to true while ETHICS.md still says *Pending*.
  - Until the script is approved, both exports carry a DRAFT mark. She gave written consent on 26 Nov, so the flag is now on and the mark is gone; the change is one line in the storyboard and a validated record in ETHICS.md.
  - Her consent would also allow an AI face. I kept the no-face version on purpose: every generated image is committed to a public repository, and her consent covers private evaluation only.
  - It is tested, and each time the gate applies it writes a `consent_gate` line to `runs.jsonl` (6 so far).
  - One "no face" prompt still showed her profile, which is why I now check every character keyframe by eye (E05, F07).
- **Measured audio and subtitles, not only listened to or watched** (E09, E10, E15).
  - Ducking: the music drops by 13 dB under speech and is unchanged in the pauses.
  - Loudness: the target holds after AAC encoding, at −14.04 LUFS and −1.76 dBTP.
  - Subtitle reading speed: at most 13.8 characters per second, with the shortest cue 3.3 s on screen, well inside common guidance for adult viewers. A test now keeps it that way (`test_subtitle_reading_speed`).
- **Reading the dependency's source before spending GPU quota** (F10). The Kaggle notebooks had never run, so before the first run I checked them against the diffusers 0.43.0 and ACE-Step 1.5 source. That found three defects a first run would have hit:
  - ACE-Step silently ignored the seeds, because `use_random_seed` defaults to true, so the three candidates could never have been reproduced.
  - Its load failures return a flag instead of raising, so a failed load would have gone unnoticed.
  - Its `pip` install cannot resolve its `uv`-only dependencies.
  
  It also confirmed that Wan 2.2 TI2V-5B image-to-video is supported through `expand_timesteps`.
- **More languages: where Gemini TTS stops being intelligible** (E16, `make langtest`). I measured it without listeners, by transcribing the TTS audio back and computing the character error rate (CER) against the text.
  - **English control: 0.000 CER**, so the round trip itself is clean.
  - **The same line, by language:** Afaan Oromo 0.108, Somali 0.197, Amharic 0.226, Tigrinya 0.270.
  - **The 9 real Amharic narration lines:** mean 0.148, or 0.123 once homophone letters are folded. About a sixth of the apparent errors are just ሕ/ህ, ሠ/ሰ and ዕ/እ, which sound the same.
  - **The meaning-changing errors cluster** on the first word of a line and on long inflected words. For example, ሠዋች ("she sacrificed") came back as ሰዎች ("people"). Place names were recognised.
  - **Tigrinya failed before speech.** The translation itself mixed Cyrillic, Latin and Georgian letters into Ge'ez words.
  - **Caveat:** the transcriber is the same model family and a weaker one, so this measures intelligibility *to Gemini*. It turns "check the pronunciation" into four specific words for a native speaker.
- **Amharic and the image model** (E01, E06). The model does not know "jebena" and drew a vase, so cultural objects are described by their shape.
- **Fallbacks are code too** (F11). During E16 the main Gemini model was overloaded, and the fallback added on day one failed with HTTP 404: the model name had been guessed and had never been run. I checked the real names with `ListModels` and fixed it.
- **A tool others can follow.**
  - An offline end-to-end test builds both exports with fake models and real FFmpeg (`tests/`, 25 tests).
  - A 61-page technical document is built from the code itself, so its excerpts cannot drift from the implementation (`make techdoc`, `PROJECT_TECHNICAL_DOCUMENTATION.pdf`).

## 7. What I would build next

1. **Choose the Amharic voice by ear, not by length.**
    - Make several TTS takes per line and have Amharic speakers compare them blind.
    - Pin the chosen take in the storyboard.
    - Why: E02 showed that the voice style instruction does not reliably control pace, and TTS has no seed, so today one take per line is luck.
2. **Detect faces in generated images automatically.**
    - Run a face detector over every character keyframe and Wan clip, and fail the stage if a face is visible while likeness consent is missing.
    - Why: E05 and F07 showed that a "no face" prompt is not a guarantee, and an eye check does not scale.
3. **Then, with consent, character consistency.** Make a character sheet, possibly train a small LoRA on it, and measure whether she stays recognisably the same person across shots.

The first is the most urgent: E16 shows the Amharic voice is the weakest link that I can measure, and it is the part the family hears.

---

## Appendix: where the evidence is

| Claim | Evidence |
|---|---|
| Audience and intent were written before generation | DESIGN.md §1; commit `1b715f8` |
| User tests: not run; status and prepared protocol | DESIGN.md §4–§6; `docs/FAMILY_KIT.md` |
| Every shot has a stated reason | DESIGN.md §3; `reason` field of every shot in `storyboard.json` |
| The storyboard is validated before every stage | `schema/storyboard.schema.json`; `pipeline/validate.py`; `tests/test_storyboard.py` |
| Only what changed regenerates | `cache_hit` vs `model_call` lines in `runs.jsonl`; `tests/test_pipeline.py` (cache tests) |
| Retries and quota handling | `pipeline/common.py`; FAILURES.md F02–F04 |
| One command from a clean clone | COSTS.md, "Local compute" (fresh clone, exit 0, 0 model calls) |
| Experiments, each with a hypothesis | EXPERIMENTS.md E01–E10, E15, E16 (E11–E14 are the Kaggle runs, not yet run) |
| Real blockers and fixes | FAILURES.md F01–F11 |
| Latency, cost and free-tier limits | COSTS.md (generated from `runs.jsonl`) |
| Consent, licences, labelling | ETHICS.md; `consent` block in `storyboard.json` |
| Both exports verified | `outputs/final/report.json` (duration, size, codecs, LUFS, true peak) |
| Full technical documentation | `PROJECT_TECHNICAL_DOCUMENTATION.pdf` (source in `docs/technical/`) |
