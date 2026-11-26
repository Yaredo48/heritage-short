# FAILURES

What broke, what I tried, and what fixed it or worked around it. Times are UTC on 25 Nov 2026 unless noted. Every model-call failure below is a line in `runs.jsonl` (`"status": "error"`).

## F01 · The virtualenv had no pip, and the smoke test had never really run
- **Symptom:** `import requests` failed inside `.venv`. The committed smoke outputs (`outputs/smoke/*.png`, `*.wav`) were 0-byte files and there was no `runs.jsonl`, so no provider had ever been called.
- **Cause:** the venv was created without `ensurepip` (Ubuntu needs `python3.12-venv`, which needs sudo). `run.py` also sat in `story/` instead of the repo root, so `python run.py` could not import `pipeline`.
- **Fix:** bootstrapped pip into the venv with the official PyPA `get-pip.py`, installed `requirements.txt`, moved `run.py` to the root, deleted the empty files and ran the smoke test for real.
- **Lesson:** an artefact that exists is not evidence that something ran. The log is.

## F02 · Gemini 3.8 Flash: 503 "high demand" on every attempt
- **Evidence:** 3 attempts at 13:49–13:50, latencies 30.4 s, 23.8 s and 35.9 s, all `503 … experiencing high demand`.
- **Tried:** the built-in retry (3 attempts, exponential backoff). Not enough: the overload outlasted it.
- **Fix:** `providers.gemini_text` falls back once to `gemini-3.8-flash-lite` on a 503 after retries (`GEMINI_TEXT_FALLBACK`). Only the optional `script` stage uses the text model; the storyboard was finished without it.

## F03 · Gemini TTS: 3 requests per minute, and the backoff burned its retries
- **Evidence:** 14:00:29 and 14:01:13–14:01:20, `429 … limit: 3 requests per minute on Free Tier. Please retry in 39s`. The old backoff waited 2 s and then 4 s, so all attempts landed inside the same minute and the run died.
- **Fix:** `common.retry_delay` reads the server's hint (the `Retry-After` header, or "retry in 39s" in the body) and waits that long. Attempts were raised from 3 to 4.

## F04 · Gemini TTS daily quota ran out in the middle of an experiment
- **Evidence:** from 14:01, `429 … limit: 10 requests per day … Please retry in 17h50m8s`. My regex did not understand `17h50m8s`, so the run fell back to 20–40 s waits and spent about 10 minutes retrying a quota that resets the next day (14:05–14:11, s04 attempts 1–4).
- **Observed limit vs stated limit:** 13 TTS calls succeeded on 25 Nov (1 smoke + 9 narration + 3 retake), and s02/s03 even succeeded on a retry after a "per day" 429. The documented "10 per day" is approximate. Budgeting assumes about 10.
- **Fix:** `common.parse_wait` understands `h/m/s`. Any suggested wait over 120 s (a daily quota, not a burst limit) now raises at once: `quota exhausted, provider asks to wait 17.8 h. Cached outputs are kept; rerun later.` Covered by `tests/test_pipeline.py::test_daily_quota_fails_fast`.
- **Workaround for the film:** the voice-style retake (E02) stopped after 3 of 9 lines. Instead of mixing two takes, I kept the complete first take and fixed timing without the model (F05).
- **Consequence for the plan:** every narration edit costs one call from a budget of about 10 per day. Family corrections to the Amharic must be batched into one session.

## F05 · The narration made the film 92 s, over the 90 s limit
- **Evidence:** `make timing` after the first take: 77.4 s of narration, 92.2 s film.
- **Cause:** the style prompt asked for "gentle pauses between phrases", and the model put 0.5–1.1 s silences between phrases (`silencedetect`: s02 had pauses of 0.63, 0.73, 1.13 and 0.85 s).
- **Tried:** FFmpeg `silenceremove` (stop_periods=-1, several thresholds, rms and peak). It only shortened s02 from 10.07 s to 9.30 s at best, and the total to 75.3 s (E03).
- **Fix:** `pipeline/audio.py::compress_pauses`, 60 lines of standard-library Python: 20 ms RMS frames, and any silence longer than `voice.max_pause_s` is cut to that length, keeping half on each side. At 0.45 s the total went from 77.4 s to 67.9 s and the film to 84.4 s. Deterministic, no model call, covered by a test.

## F06 · "Jebena" was drawn as a vase, then as a pot with a pipe
- **Evidence:** smoke test (`outputs/smoke/flux_klein_512.png`): "a clay coffee pot (jebena)" became a plain terracotta vase. In s04, "a long narrow neck" became a pot with a long black pipe.
- **Fix:** describe the shape rather than the name ("a small round black clay coffee pot with a short spout"). "Handleless cups" is still ignored (E05, E06). It is accepted for now; the cup's real look is a question for the family.

## F07 · A "no face" prompt still showed a face (consent risk)
- **Evidence:** s04, first keyframe (`outputs/keyframes/s04_642fa6f9145d.png`): "from behind and slightly to the side … face hidden by a shawl" showed her eye and nose in profile.
- **Why it matters:** consent for her likeness is still pending, so a visible face is not allowed.
- **Fix:** "seen from directly behind, her back to the camera so her face is not visible". I now check every character keyframe by eye, and the Wan export adds "she keeps her back to the camera" to those motion prompts.

## F08 · Conditioning on a style reference made keyframes worse
- **Evidence:** E07: with the chosen style sheet as `input_image_0`, FLUX.2 klein copied the sheet's table, pot and cup into the Sheka forest (s02), and s05 lost the dress and lamp continuity.
- **Fix:** `style.use_style_reference = false`. The text style block alone keeps the look consistent. The reference images are kept for the record.

## F09 · Small FFmpeg breakages while building assembly
- `aevalsrc` parsed the commas inside the chord expression as option separators ("No option name near '48000:d=90'"). Fixed by quoting the expression (`exprs='…'`).
- Paths with spaces (`week 0/challenge 2`) break the `ass=` subtitle filter. Fixed by running FFmpeg with `cwd` set to the work folder and passing only the file name.
- The vertical subtitles first produced a one-word cue ("story."). Fixed with balanced wrapping (E08).

## F10 · The Kaggle notebooks had three defects that a first run would have hit
- **How found:** before the first Kaggle run (26 Nov), I checked the notebooks against the library source: the diffusers 0.43.0 wheel and a clone of the ACE-Step 1.5 repository (`acestep/inference.py`, `docs/en/INFERENCE.md`, `pyproject.toml`).
- **ACE-Step seeds were silently ignored.** `GenerationConfig.use_random_seed` defaults to `True`, and then `prepare_seeds` draws random seeds whatever `seed` says. The three "seed 11/22/33" candidates would have been unreproducible. Fixed: `use_random_seed=False, seeds=[seed]`.
- **ACE-Step failures would not raise.** `initialize_service()` and `LLMHandler.initialize()` return `(status, ok)` instead of raising. The LM checkpoint is not downloaded automatically, and the LM runs in bfloat16, which a T4 lacks. Fixed: the `ok` flag is checked, and the optional LM planner is dropped (caption, bpm and key are given explicitly).
- **ACE-Step install.** `pip install -e .` cannot work: `pyproject.toml` pins `torch==2.10.0+cu128` from a PyTorch index and a local `nano-vllm` that only `uv` resolves. Fixed: the official `uv sync` into `/tmp` and a generation script run with `uv run`.
- **Wan 2.2.** The model card only shows text-to-video. The diffusers source confirms that `WanImageToVideoPipeline` supports TI2V-5B through `expand_timesteps` ("Wan2.2 ti2v"). Fixed: pinned `diffusers==0.43.0`, `expand_timesteps=True` passed explicitly, and a check that rejects black or NaN frames. Character shots are excluded by default (consent).
- **Lesson:** "not run yet" code is untested code; reading the dependency's source is cheaper than a failed GPU session.

## Pending (filled in after the Kaggle runs)

| Stage | What happened | What I tried | Resolution |
|---|---|---|---|
| Wan 2.2 on Kaggle T4 | _to fill: e.g. OOM, fp16 NaN, time per clip_ | | |
| ACE-Step 1.5 on Kaggle | _to fill: install, LM planner, API names_ | | |
