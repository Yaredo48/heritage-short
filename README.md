# The Silent Language of a Mother's Love

A 60–90 second short film about my mother, who grew up in Yeki Woreda, Sheka Zone, in southwest Ethiopia, and the sacrifices she made for her children. It is narrated in Amharic with English subtitles and an original score, and exported in 9:16 and 16:9.

The film is not edited by hand. This repository is a small pipeline that turns one file, [`storyboard.json`](storyboard.json), into keyframes, moving shots, music, narration and a finished, verified edit. One command rebuilds it.

```bash
make film
```

## For assessors: where each criterion is evidenced

| Criterion | Where to look | In one line |
|---|---|---|
| **Software engineering and reproducibility** | [`storyboard.json`](storyboard.json) + [`schema/`](schema/storyboard.schema.json) + [`pipeline/validate.py`](pipeline/validate.py); [`pipeline/common.py`](pipeline/common.py); [`runs.jsonl`](runs.jsonl); [`tests/`](tests/); [`.github/workflows/tests.yml`](.github/workflows/tests.yml); [COSTS.md](COSTS.md) "Local compute" | The contract is validated before every stage. Outputs are cached by content hash, so only changed shots regenerate (tested). Retries read the provider's wait hint and fail fast on daily quotas. No secrets are committed (`.env` is ignored). Every model call is logged. **`make film` on a fresh clone: exit 0, 0 model calls, 18 cache hits.** 25 offline tests |
| **Documentation** | this README, [ARCHITECTURE.md](ARCHITECTURE.md), [PROJECT_TECHNICAL_DOCUMENTATION.pdf](PROJECT_TECHNICAL_DOCUMENTATION.pdf), [docs/technical/SETUP_GUIDE.md](docs/technical/SETUP_GUIDE.md) | Contracts, cache keys and failure handling, with diagrams. The 62-page technical PDF is built from the code (`make techdoc`), so its excerpts match the repository |
| **Design thinking and audience** | [DESIGN.md](DESIGN.md) | Audience and intent were written before any generation (§1, commit `1b715f8`). Every shot has a stated reason (§3). The user tests were **not run**; this is stated, not hidden (§4–§5, questionnaires prepared). Automated checks are labelled as not audience evidence (§6) |
| **Experimentation and iteration** | [EXPERIMENTS.md](EXPERIMENTS.md) | 12 experiments run (E01–E10, E15, E16), each hypothesis → one change → measured result → decision. E11–E14 (Kaggle) were not run |
| **Troubleshooting and persistence** | [FAILURES.md](FAILURES.md) | 11 real blockers (F01–F11): quota, overload, language, consistency, consent risk, tooling. Each says what was tried and what fixed it |
| **Measurement** | [COSTS.md](COSTS.md) (generated from `runs.jsonl` by `make costs`), [`outputs/final/report.json`](outputs/final/report.json), [`outputs/langtest/summary.json`](outputs/langtest/summary.json) | Latency, failures and cache hits per stage and model; list-price equivalent; free-tier limits found; loudness, ducking, subtitle speed and intelligibility measured. No GPU minutes, because Kaggle was not run; no frontier access |
| **Consent, labelling and licences** | [ETHICS.md](ETHICS.md) | Written consent recorded 26 Nov 2026 (scope: the assignment and its private evaluation). A consent gate in code (no face, DRAFT mark until approval). Licences of every model and output. Labelling plan (AI end card, metadata, no public posting) |

## Status on 26 Nov 2026

- **Done and verified.**
  - Both exports are 84.42 s, at 1080×1920 and 1920×1080, H.264/AAC, −14.04 LUFS and −1.76 dBTP, with burned-in English subtitles and an AI end card. There is no DRAFT mark, and all six checks in `report.json` pass.
  - The Amharic narration is 9 lines in a stock Gemini voice. The keyframes are 9 FLUX.2 klein stills, with the mother shown only from behind or through her hands.
- **Not done.**
  - The Kaggle GPU stages: the Wan 2.2 notebook (moving clips) and the ACE-Step notebook (score) are written and checked against the libraries' source (F10), but not run. All shots are therefore slow pan-and-zoom moves over stills, and the music is a temporary FFmpeg pad.
  - The two audience tests were not run.

## Contributions

- **Author (Yared).**
  - Chose the story, the subject (his mother) and the audience.
  - Wrote the story notes and the audience and intent brief before anything was generated (`story/notes.md`, DESIGN.md §1, commit `1b715f8`).
  - Set the project's constraints: free tools only, a stock voice and never a clone, no face until consent, Kaggle runs uploaded by hand.
  - Obtained his mother's written consent.
  - Directed the work through the instructions and decisions recorded here, and ran it with his own API and Kaggle accounts.
- **Coding agent (Claude Code, Anthropic).**
  - Wrote the pipeline code, tests, Kaggle notebooks and documentation under the author's direction.
  - Drafted storyboard v1 from the author's notes (its changelog says so).
  - Ran the experiments and recorded each experiment and failure.
  - Commits from `22b22dd` onwards carry a `Co-Authored-By: Claude` trailer. The first four commits (skeleton, design brief, story notes, core library) are recorded under the author's name.
- **Generative models.** The images (FLUX.2 klein 4B) and the voice (Gemini 3.8 Flash TTS) are AI-generated; see ETHICS.md for licences.

The brief suggests "letting the agent write the stage scripts while you design and review"; this project followed that division of work.

## What it does

| Stage | Command | Model / tool | Runs on |
|---|---|---|---|
| validate | `make validate` | JSON Schema + consent checks | laptop |
| 4 · narration | `make narration` | Gemini 3.8 Flash TTS, stock voice (Amharic) | Gemini API, free tier |
| 1 · keyframes | `make refs`, `make keyframes` | FLUX.2 klein 4B | Cloudflare Workers AI, free tier |
| 2 · moving shots | `make shots` | Wan 2.2 TI2V-5B clip, else Ken Burns in FFmpeg | Kaggle T4 (notebook) / laptop |
| 3 · music | `make music` | ACE-Step 1.5 candidates, else a temp pad | Kaggle T4 (notebook) / laptop |
| 5 · assembly | `make assemble` | FFmpeg: crossfades, ducking, subtitles, loudness, end card, both aspect ratios | laptop |

Every stage validates the storyboard first, skips work whose inputs have not changed, and appends one line per model call to [`runs.jsonl`](runs.jsonl). How the stages fit together, the cache keys and the failure handling are in [ARCHITECTURE.md](ARCHITECTURE.md). Measured time and cost are in [COSTS.md](COSTS.md). The complete technical documentation, with architecture and pipeline diagrams, is [PROJECT_TECHNICAL_DOCUMENTATION.pdf](PROJECT_TECHNICAL_DOCUMENTATION.pdf); a short install guide is [docs/technical/SETUP_GUIDE.md](docs/technical/SETUP_GUIDE.md).

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
3. Download `heritage_results_wan.zip` and `heritage_results_music.zip` from the notebooks' output, then run `make import ZIP=…` once for each.
4. For each clip you like, set that shot's `"video": "wan"`. Listen to the music candidates under the narration and set `music.chosen_seed` and `music.choice_reason`.
5. `make film`.

The notebooks save each result as soon as it is made and skip finished ones, so a timed-out session loses nothing.

## Consent and labelling

My mother's AI likeness is gated in code. Her written consent was recorded in [ETHICS.md](ETHICS.md) on 26 Nov 2026, for this assignment and its private evaluation. So:
- the narration is approved (`consent.script_approved`), and the exports carry no DRAFT mark;
- the film keeps its no-face version (`consent.likeness_approved` stays false), because every image in this public repository would otherwise show an AI face representing her;
- the film is shared privately with the assessors, not posted publicly.

The narration uses a stock Gemini voice; her voice is never cloned. The film ends on an AI-disclosure card.

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
PROJECT_TECHNICAL_DOCUMENTATION.pdf   full technical documentation (source: docs/technical/, `make techdoc`)
```
