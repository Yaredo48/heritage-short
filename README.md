# The Silent Language of a Mother's Love

A 60–90 second short film about my mother, who grew up in Yeki Woreda, Sheka Zone, in southwest Ethiopia, and the sacrifices she made for her children. It is narrated in Amharic with English subtitles and an original score, and exported in 9:16 and 16:9.

The film is not edited by hand. This repository is a small pipeline that turns one file, [`storyboard.json`](storyboard.json), into keyframes, moving shots, music, narration and a finished, verified edit. One command rebuilds it.

```bash
make film
```

## What it does

| Stage | Command | Model / tool | Runs on |
|---|---|---|---|
| validate | `make validate` | JSON Schema + consent checks | laptop |
| 4 · narration | `make narration` | Gemini 3.8 Flash TTS, stock voice (Amharic) | Gemini API, free tier |
| 1 · keyframes | `make refs`, `make keyframes` | FLUX.2 klein 4B | Cloudflare Workers AI, free tier |
| 2 · moving shots | `make shots` | Wan 2.2 TI2V-5B clip, else Ken Burns in FFmpeg | Kaggle T4 (notebook) / laptop |
| 3 · music | `make music` | ACE-Step 1.5 candidates, else a temp pad | Kaggle T4 (notebook) / laptop |
| 5 · assembly | `make assemble` | FFmpeg: crossfades, ducking, subtitles, loudness, end card, both aspect ratios | laptop |

Every stage validates the storyboard first, skips work whose inputs have not changed, and appends one line per model call to [`runs.jsonl`](runs.jsonl). How the stages fit together, the cache keys and the failure handling are in [ARCHITECTURE.md](ARCHITECTURE.md). Measured time and cost are in [COSTS.md](COSTS.md).

## Install

Needs Python 3.11+, FFmpeg 6+ (with libass) and `make`.

```bash
git clone https://github.com/Yaredo48/heritage-short.git && cd heritage-short
make setup                 # .venv + requirements.txt
cp .env.example .env       # then fill in the keys below
make smoke                 # calls each provider once; prints a table
```

If `python3 -m venv` fails with "ensurepip is not available" (Ubuntu without `python3.12-venv`), install that package, or bootstrap pip into the venv with the official `get-pip.py` (see FAILURES.md F01).

## Configuration

All keys live in `.env`, which is git-ignored. Nothing secret is ever written to the log.

| Variable | Where to get it | Used by |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio → *Get API key* (free tier) | narration, script |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Cloudflare dashboard → Workers AI → *Use REST API* (token with Workers AI permission) | keyframes |
| model names | defaults in `.env.example` | all |

A clean clone already contains every model output (keyframes, narration, music, any Wan clips), so `make film` on a fresh machine is all cache hits plus FFmpeg. It makes no API calls and needs no keys unless you change the storyboard.

## Run it

```bash
make film          # validate → narration → keyframes → shots → music → assemble
make radio         # radio cut (narration + score on black, subtitled) for user tests
make timing        # narration length vs shot length, before rendering
make test          # offline tests: fake models, real FFmpeg (~1 min)
make costs         # refresh the table in COSTS.md from runs.jsonl
make help          # every target
```

Outputs: `outputs/final/the_silent_language_of_a_mother_s_love_vertical.mp4` and `..._horizontal.mp4`, `subtitles_en.srt`, and `report.json` (duration, size, loudness and pass/fail checks for both files).

## Change one shot and regenerate only that shot

1. Edit that shot in `storyboard.json`: its `image_prompt` (or `no_face_prompt`), `seed`, `kenburns`, or its `narration.am` line.
2. `make shot SHOT=s03` (or just `make film`: the cache does the same).
3. Check `runs.jsonl`: one new `model_call` line for `s03`, and `cache_hit` lines for everything else.

`--force` regenerates even when nothing changed, for a new take with the same prompt: `.venv/bin/python run.py keyframes --shot s03 --force`.

## GPU stages (Wan 2.2 and ACE-Step) on Kaggle

1. `make kaggle-export` → `kaggle/heritage_job.zip` (keyframes + `jobs.json`).
2. On Kaggle (phone-verified account): *Datasets → New* → upload the zip. Open `notebooks/wan_video.ipynb` and `notebooks/ace_step_music.ipynb`, *Add input* → the dataset, set *Accelerator: GPU T4* and *Internet: on*, and run all.
3. Download `heritage_results.zip` from each notebook's output, then run `make import ZIP=~/Downloads/heritage_results.zip`.
4. For each clip you like, set that shot's `"video": "wan"`. Listen to the music candidates under the narration and set `music.chosen_seed` and `music.choice_reason`.
5. `make film`.

The notebooks save each result as soon as it is made and skip finished ones, so a timed-out session loses nothing.

## Consent and labelling

My mother's AI likeness is gated in code. Until her consent is recorded in [ETHICS.md](ETHICS.md) *and* `consent.likeness_approved` is set, shots of her are generated from behind or as hands only. Until she approves the narration (`consent.script_approved`), every export carries a DRAFT mark. The narration uses a stock Gemini voice and her voice is never cloned. The film ends on an AI-disclosure card, and posts are made with the platform's AI label on.

## Repository

```
storyboard.json   the contract: shots, durations, prompts, seeds, narration, music, mix, consent
schema/           JSON Schema for the storyboard
pipeline/         one module per stage (see ARCHITECTURE.md)
notebooks/        Kaggle notebooks for Wan 2.2 and ACE-Step 1.5
outputs/          generated references, keyframes, narration, music, shots, final films
runs.jsonl        one line per model call
tests/            pytest, offline
DESIGN.md  ARCHITECTURE.md  EXPERIMENTS.md  FAILURES.md  COSTS.md  ETHICS.md
docs/             report draft (`make report` -> PDF/Word), walkthrough plan, post notes, interview prep
SUBMISSION.md     what each assignment needs, its status, and the remaining steps
```
