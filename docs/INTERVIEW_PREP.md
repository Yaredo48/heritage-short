# Interview preparation

The brief says the AI interviewer will ask:
1. Why the pipeline is shaped the way it is.
2. To walk through an entry in your experiment log.
3. To describe a failure and what you did about it.
4. What your audience told you, and what changed because of it.

It also checks "whether the repository reflects your own understanding". Answer in your own words. The points below are reminders of what is in the repo, not a script. Reread the files named before the interview.

## 1. "Why is your pipeline shaped this way?"

Reread: ARCHITECTURE.md, `storyboard.json`, `pipeline/common.py`.

- **One contract, `storyboard.json`, validated by a JSON Schema before every stage.** Every stage reads the same file, so a typo is caught before any model call, and changing one shot is one edit.
  - The schema forces a `reason` for every shot and a `no_face_prompt` for every shot that shows her.
  - The validator also checks the total length is 60–90 s and the seeds are consistent.
- **Five stages, one file each.** Each stage can run, fail and be rerun on its own (`make keyframes`, `make shot SHOT=s03`).
- **Narration comes before pictures.** The Amharic takes set each shot's length, `max(planned, lead-in + narration + 0.6 s)`. That is how I found the 92 s problem before animating anything.
- **Content-hash caching.** Each output's filename includes a hash of everything that affects it: prompt, seed, size, model, references, voice and text.
  - Same inputs give the same file, which means a `cache_hit` and no API call.
  - Why it matters here: the TTS free tier is about 10 calls a day, so regenerating everything was not an option.
- **Retries that read the server.** The pipeline waits as long as the 429 response asks. If that is more than 2 minutes it is a daily quota, so it stops at once and keeps everything cached.
- **GPU stages on Kaggle by hand.** I have no GPU, so `make kaggle-export` packs the jobs, I run the notebooks, and `make import` brings back the clips and their log lines.
  - Without Wan clips, every shot falls back to an FFmpeg Ken Burns pan, so the film always builds.
- **Consent enforced in code.** With no recorded consent, the pipeline uses no-face prompts, generates no character sheet and adds a DRAFT mark. The validator will not accept the consent flag while ETHICS.md says *Pending*.

Likely follow-up: *"What would you change?"* ✍️ Your view. For example: the Kaggle step is manual, and the TTS has no seed, so takes cannot be reproduced exactly.

## 2. "Walk me through one experiment."

Reread: EXPERIMENTS.md. Know **E07** and **E04** well. Use the shape hypothesis → one change → measured result → decision.

- **E07, style reference vs text style block.**
  - *Hypothesis:* conditioning every keyframe on one style sheet makes the look more consistent.
  - *Change:* `use_style_reference: true` for s02 and s05, keeping the same prompts and seeds.
  - *Result:* worse. The sheet's table and pot were pasted into the forest, and s05 lost the dress and lamp. FLUX.2 klein edits an input image; it does not borrow its style.
  - *Decision:* turned it off; the text style block keeps the look consistent. This is also the "practice that did not work" in the report.
- **E04, the pause cap.**
  - *Change:* `voice.max_pause_s` set to 0.35, 0.45 and 0.55 s, with no model calls.
  - *Result:* 65.3, 67.9 and 70.0 s of narration.
  - *Decision:* 0.45 s gives an 84.4 s film. It still needs native ears to confirm it sounds natural (user test 1).
- **E16, more languages, ASR round trip.**
  - *Hypothesis:* if TTS speaks a line well, transcribing it back recovers the text; the English control should be about 0.
  - *Result:* English 0.000; s01 line: Oromo 0.108, Somali 0.197, Amharic 0.226, Tigrinya 0.270. Amharic narration mean 0.148, or 0.123 with homophones folded; errors on first words and long inflected words; Tigrinya's *translation* had Cyrillic and Georgian letters in it.
  - *Caveat:* the same model family transcribes, so it is intelligibility to Gemini, not to people.
- Others worth knowing:
  - **E01:** "jebena" was drawn as a vase.
  - **E05:** a "no face" prompt still showed a profile.
  - **E09:** the AAC encode added 0.2 dB of peak, so it needed a pre-limiter.
  - **E10:** ducking measured at −13 dB under speech.

Likely follow-up: *"How do you know it wasn't just the seed?"* Seeds were fixed and only one field changed. In E02 (TTS) there is no seed, so it says take-to-take variance is unknown.

## 3. "Tell me about a failure."

Reread: FAILURES.md F03–F05 (the strongest) and F01, F07.

- **F04, the daily TTS quota.**
  - My parser did not understand "retry in 17h50m8s", so the run spent about 10 minutes retrying a quota that resets the next day.
  - Fix: the parser now handles hours, minutes and seconds, and any wait over 2 minutes fails at once with a clear message. There is a test for it.
  - Consequence: narration edits must be batched.
- **F05, the film was 92 s.** The style prompt made the TTS pause about 1 s between phrases, and FFmpeg's `silenceremove` barely helped. I wrote a pause compressor: 67.9 s of narration, an 84.4 s film, and no model calls.
- **F01, the smoke test had never run.** The output files were 0 bytes and there was no log. Lesson: a file existing is not evidence; the log is.
- **F07, a "no face" prompt showed her profile.** That is a consent risk. I rewrote it to "directly behind, her back to the camera", and I now check every character keyframe by eye.

## 4. "What did your audience tell you, and what changed?"

Reread: DESIGN.md §4 and §5, and the `changelog` in `storyboard.json` (versions 2 and 3).

This is the one question the repo cannot answer for you. Know:
- who you showed each cut to, and how;
- one quote you remember;
- the one change you made because of it, and which line or shot it touched.

If a test did not happen, say so plainly. Do not invent it.

## Numbers worth knowing

| | |
|---|---|
| Film length | 84.4 s (60–90 required); 9 shots plus a 3 s end card |
| Loudness | −14.04 LUFS integrated, −1.76 dBTP true peak (both exports) |
| Ducking | music −13 dB under speech, unchanged in pauses |
| TTS free tier | 3 requests/min, about 10/day; 13 calls succeeded on 25 Nov |
| Keyframes | FLUX.2 klein 4B, about 10 s per image; about 104 neurons per 1024² image, about 95 images/day free |
| Fresh clone | `make film`: exit 0, 7 min 40 s, 0 model calls, 18 cache hits |
| Tests | 24, offline, about 50 s |
| Cost | USD 0 actual. List-price equivalent for the keyframes is about USD 0.02 (COSTS.md) |
