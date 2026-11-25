# Report: The Silent Language of a Mother's Love

_B2W0 AI-Content Generation: codebase and report. Repository: https://github.com/Yaredo48/heritage-short_

> **How to use this draft:** sections marked ✍️ need your own words and real events. Everything else points to evidence already in the repository; check each claim against the file named before submitting. Export to PDF when done.

## 1. What I set out to make, and for whom

A 60–90 second film about my mother, who grew up in Yeki Woreda, Sheka Zone, and gave up her own comfort and dreams so her children could have the chances she did not. It is for my family, at home and abroad, watching on phones in our Telegram group. At the end they should recognise that her love was shown through what she gave and endured, not only through what she said. (DESIGN.md §1, written before any generation.)

The film: Amharic narration (stock Gemini TTS voice), English subtitles, an original score ducked under the voice, an AI-disclosure end card, 9:16 and 16:9, about 84 s. The pipeline: one validated `storyboard.json` feeding five stages (keyframes, moving shots, music, narration, assembly), with content-hash caching, retries that read the provider's own wait hint, and one log line per model call. `make film` rebuilds everything; a clean clone makes no API calls because every model output is committed and cached.

## 2. What I learned from my audience ✍️

- First test, radio cut (DESIGN.md §4): who, what they said, the insight.
- What changed in `storyboard.json` because of it (version 2, changelog line).
- Second test, near-final cut (DESIGN.md §5): what they said, what changed (version 3).

## 3. The hardest problem and how I solved it

**Candidate (from the logs): the narration did not fit the film, and the TTS quota made retakes nearly impossible.** ✍️ Confirm or choose another.

- The first full Amharic take was 77.4 s of speech, which made the film 92.2 s, over the 90 s limit (`make timing`; FAILURES F05). The cause was the style instruction "gentle pauses between phrases": the model put 0.5–1.1 s silences between phrases.
- The obvious fix, a retake with a faster style, ran into the Gemini TTS free tier: 3 requests/minute and about 10/day. The retake stopped after 3 lines. Those 3 lines were only 12 % shorter on average, and one was longer (E02, F03, F04).
- FFmpeg's `silenceremove` barely helped (77.4 → 75.3 s, E03). I wrote a 60-line pause compressor that cuts any silence longer than 0.45 s down to 0.45 s: 77.4 → 67.9 s and a film of 84.4 s, with **zero extra model calls**. The original takes stay untouched in `outputs/narration/raw/`, and the setting is one number in the storyboard (`voice.max_pause_s`), part of the cache key (E04).
- The same episode fixed the retry logic: the old backoff waited 2–4 s against a 39 s limit, and then spent 10 minutes retrying a quota that reset in 17 hours. Retries now use the server's hint and fail fast on daily quotas (`test_daily_quota_fails_fast`).

## 4. A suggested practice that beat my instinct ✍️

Candidates with evidence (pick the one that is true for you):
- **Timing the narration first.** The narration set every shot length (`narration.timeline`), and it showed the 92 s problem before any picture was animated.
- **Logging every call.** `runs.jsonl` is how I found that the smoke test had never actually run (F01), and how I could tell the per-minute limit from the per-day one (F03 vs F04).
- **A JSON contract with a schema.** The consent gate lives in the contract: the validator refuses `likeness_approved: true` while ETHICS.md says *Pending*.

## 5. A suggested practice that did not work as expected

**"Make a reference sheet first, then condition every keyframe on it."** With FLUX.2 klein the style reference made shots worse. The model edits the input image instead of borrowing its style, so the table and pot from the reference appeared in the middle of the Sheka forest (s02), and the hands shot (s05) lost the costume continuity (E07, same prompts and seeds, with and without the reference). A shared text style block attached to every prompt kept the look consistent. ✍️ Add what you think this means; the character sheet is still untested because consent is pending.

## 6. Beyond the floor ✍️

What exists in the repository today:
- **A consent gate in code** (no-face variants, no character sheet, a hidden face in Wan prompts, a DRAFT mark until script approval), tested.
- **Measured audio engineering:** ducking measured as −13 dB under speech and 0 dB in pauses (E10); a loudness target that survives AAC encoding (E09).
- **An offline end-to-end test** with fake models and real FFmpeg: both exports, 60–90 s, right size, audio and subtitles.
- ✍️ Anything else you add: Wan vs Ken Burns preference test, Amharic pronunciation findings, a second language.

## 7. What I would build next ✍️

Ideas: per-line TTS takes compared blind by Amharic speakers; a character LoRA once consent is given; a "tell your story" form for relatives that writes a storyboard.json.
