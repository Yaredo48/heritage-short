<!--
{
  "title": "The Silent Language of a Mother's Love",
  "subtitle": "Design, implementation and operation of a reproducible generative-AI film pipeline",
  "lede": "How one validated <code>storyboard.json</code> becomes a narrated, scored, subtitled and loudness-verified 60–90 second film in two aspect ratios, using free-tier generative models, content-addressed caching, quota-aware retries and a consent gate enforced in code.",
  "control": [
    ["Project", "Heritage Short: B2W0 AI-Content Generation challenge"],
    ["Repository", "github.com/Yaredo48/heritage-short (branch <code>main</code>)"],
    ["Document version", "1.0, 26 November 2026"],
    ["Code baseline", "commit <code>5617003</code> plus this documentation commit"],
    ["Pipeline state", "Film built and verified (84.42 s, both aspect ratios), no DRAFT mark. Consent recorded 26 Nov (private evaluation). Kaggle GPU stages implemented but not yet run; audience tests not run."],
    ["Audience", "Developers and technical reviewers who want to understand, reproduce or extend the pipeline"]
  ],
  "note": "Every code excerpt in this document is extracted from the repository at build time by <code>docs/technical/build_pdf.py</code>, with its file name and line numbers. Measurements are taken from <code>runs.jsonl</code>, <code>outputs/final/report.json</code> and test runs; anything not yet executed is marked as such."
}
-->

---

# Project Introduction

## Background and motivation

The project answers the B2W0 challenge *AI-Content Generation: The Heritage Short*. The brief asks for a 60–90 second film about a real family story, made with generative models available at zero cost from Ethiopia. It has to be exported in vertical (9:16) and horizontal (16:9) formats, and be **produced by code** from a written storyboard rather than edited by hand.

The story chosen is the author's mother. She grew up in Yeki Woreda, Sheka Zone, in southwest Ethiopia, and gave up her own comfort and dreams so her children could have chances she never had. The intended audience is the family itself, watching on phones in a family Telegram group (DESIGN.md §1, written before any generation). The film is narrated in **Amharic** with **English subtitles**. A recurring object, *her old coffee cup*, opens and closes it.

The motivation is twofold:

- **Emotional.** Make a tribute the family will keep.
- **Technical.** Show that a small, honest engineering pipeline can turn unreliable, rate-limited, free generative services into a reproducible product. Unreliable here means models that return 503s and quotas of about ten calls a day.

## Problem statement

Generative media tools are usually driven by hand, in web interfaces. That makes a film impossible to reproduce, hard to revise one shot at a time, and expensive in quota, because every change tends to regenerate everything. Under the constraints of this project that is not acceptable.

Table: Constraints that shaped the problem.

| Constraint | Consequence for the design |
|---|---|
| Free tiers only, no payment card | Gemini TTS allows **3 requests/minute and about 10/day**; Cloudflare allows 10,000 neurons/day. Every call must be reused, never repeated |
| No local GPU | Image-to-video (Wan 2.2) and music (ACE-Step 1.5) can only run in Kaggle notebooks, outside the local pipeline |
| A real person is the subject | Her likeness and the words spoken about her need recorded consent; until then the pipeline must not show her face |
| Graded by reading code, logs and documents | Every claim must be backed by a log line, a test or a written record |
| 60–90 s, two aspect ratios, subtitles, AI end card | The edit must be computed from data, so both exports are always consistent |

**Problem:** build a pipeline that turns one declarative storyboard into a finished film. It must regenerate only what changed, survive provider failures, keep within free quotas, enforce consent, log every model call, and run end to end with one command from a clean clone.

## Project objectives

1. **One contract.** A single `storyboard.json`, validated by JSON Schema and cross-field rules before any stage runs.
2. **Five independent stages.** Keyframes, moving shots, music, narration and assembly, each runnable alone (`make keyframes`, `make shot SHOT=s03`).
3. **Content-addressed caching.** An output is regenerated only when one of its inputs changes.
4. **Resilient model calls.** Retries that honour the provider's own wait hint and fail fast on daily quotas.
5. **Complete observability.** One JSON line per model-call attempt and per pipeline event in `runs.jsonl`.
6. **A consent gate in code.** No face without recorded consent, and a visible DRAFT mark until the script is approved.
7. **Verified output.** Both exports checked automatically for duration, size, codecs, loudness and true peak.
8. **Reproducibility.** `make film` on a fresh clone rebuilds the film without API keys.

## Scope and limitations

Table: What is in scope, and its state at the time of writing (26 Nov 2026).

| Item | State |
|---|---|
| Storyboard schema, validation, consent gate | Implemented and tested |
| Narration (Gemini 3.8 Flash TTS, stock voice *Charon*) with deterministic pause compression | Implemented, executed: 9 lines generated |
| Keyframes (FLUX.2 klein 4B on Cloudflare Workers AI) | Implemented, executed: 9 keyframes plus 4 style-sheet candidates |
| Moving shots: Ken Burns fallback in FFmpeg | Implemented, executed for all 9 shots |
| Moving shots: Wan 2.2 TI2V-5B clips via Kaggle | Notebook and import path implemented; **notebook not yet run** |
| Music: ACE-Step 1.5 candidates via Kaggle | Notebook and import path implemented; **notebook not yet run**. A synthesised FFmpeg placeholder pad is used meanwhile |
| Assembly: crossfades, ducking, subtitles, loudness, end card, two exports, verification | Implemented, executed, verified |
| Radio cut for audience testing | Implemented, executed |
| Script drafting with Gemini text (`run.py script`) | Implemented; **never executed** (the storyboard was drafted by the coding agent from the story notes, as its changelog records) |
| Cost summary from the log (`make costs`) | Implemented, executed |
| Language intelligibility test by ASR round trip (`make langtest`, E16) | Implemented, executed: 9 Amharic lines + 4 languages |
| Graphical user interface | Out of scope: the pipeline is a command-line tool |

Outside the code, two facts shape the release:

- The mother's written consent was recorded on 26 November. It covers the assignment and its private evaluation only, so the film is shared privately and the no-face version is kept.
- The two audience tests were not run before the deadline; DESIGN.md says so.

Chapter 11 lists all limitations.

## Expected outcomes

- A 60–90 s film in 1080×1920 and 1920×1080 H.264/AAC MP4, with burned-in English subtitles, an SRT file and an AI-disclosure end card.
- A `report.json` proving each export meets its technical targets.
- A complete `runs.jsonl` from which latency and list-price cost are computed (COSTS.md).
- A repository a stranger can clone and rebuild with `make film`.

The current film meets these targets except for the elements still pending: the Kaggle stages (score and moving shots) and the audience tests. Both exports measure **84.42 s, −14.04 LUFS integrated loudness and −1.76 dBTP true peak**, and pass all six checks (Section 9.5).

## Overview of the pipeline

`make film` runs six commands in a fixed order: `validate`, `narration`, `keyframes`, `shots`, `music`, `assemble`. Narration runs **before** pictures on purpose. The length of each spoken Amharic line decides how long its shot lasts, so the timing of the whole film is known before a single frame is rendered.

Table: The stages at a glance (numbering follows the brief's stage list; execution order is shown in the first column).

| Run order | Stage | Purpose | Model or tool | Output |
|---|---|---|---|---|
| 0 | validate | Reject an invalid storyboard before any call | jsonschema + custom checks | none (stops on error) |
| 1 | Stage 4 · narration | One Amharic WAV per shot | Gemini 3.8 Flash TTS | `outputs/narration/…` |
| 2 | Stage 1 · keyframes | One still per shot | FLUX.2 klein 4B | `outputs/keyframes/…` |
| 3 | Stage 2 · shots | One moving segment per shot and aspect | Wan 2.2 clip or FFmpeg Ken Burns | `outputs/shots/…` |
| 4 | Stage 3 · music | Prepare the score | ACE-Step 1.5 or FFmpeg pad | `outputs/music/…` |
| 5 | Stage 5 · assemble | Mix, edit, subtitle, export, verify | FFmpeg, Pillow | `outputs/final/…` |

Chapter 3 describes the architecture and Chapter 5 follows every stage in detail.

# Technology Stack and Tools

## Selection principles

Every technology had to satisfy four conditions:

1. Usable from Ethiopia **without payment**.
2. Callable from a script, so the pipeline is reproducible.
3. Small enough to understand completely.
4. Measurable, so latency and cost can be logged.

Where a choice existed, the simplest option that met the brief won. For example, plain `requests` instead of provider SDKs, and Make instead of a workflow engine.

## Language and runtime

### Python 3.12

- **What:** the implementation language of the whole pipeline (`run.py`, `pipeline/`, `tests/`). The repository was developed and tested with Python 3.12.3; the README asks for 3.11 or newer, because the code uses `from __future__ import annotations` and modern type syntax.
- **Why:** the ecosystem has mature HTTP, JSON Schema and imaging libraries, it is the language the GPU notebooks also use, and the standard library alone covers hashing (`hashlib`), WAV processing (`wave`, `array`) and subprocess control.
- **Where:** everywhere except FFmpeg filter graphs. The pause compressor (`pipeline/audio.py`) is pure standard-library Python.

### Virtual environment (`.venv`)

`make setup` creates `.venv` and installs the pinned requirements. The Makefile calls the interpreter as `"$(PY)"`, defaulting to `.venv/bin/python`. It is quoted because the author's repository path contains spaces (`week 0/challenge 2`), which broke unquoted invocations (commit `19f4e83`).

## Python libraries

@@lines requirements.txt:1-6

Table: Python dependencies, with their role.

| Library | Version | Role | Used in |
|---|---|---|---|
| requests | 2.34.2 | HTTPS calls to Gemini and Cloudflare; `HTTPError`, `ConnectionError` and `Timeout` drive the retry classifier | `providers.py`, `common.py` |
| jsonschema | 4.26.0 | Draft 2020-12 validation of the storyboard (`Draft202012Validator`) | `validate.py` |
| Pillow | 12.3.0 | Converts model images to PNG, makes the contact sheet, draws the end card and the DRAFT mark, shrinks reference images for upload | `keyframes.py`, `assemble.py`, `providers.py` |
| python-dotenv | 1.2.3 | Loads API keys from `.env` into the environment at import time | `common.py` |
| pytest | 9.2.0 | Offline test suite with fixtures and monkeypatching | `tests/` |
| markdown | 3.11.4 | Converts Markdown reports to HTML for PDF export (documentation tooling only, not used by the film pipeline) | `docs/export_report.py`, `docs/technical/build_pdf.py` |

## Generative models and services

Table: External models, how they are reached, and why they were chosen.

| Model | Provider and access | Why it was selected | Role |
|---|---|---|---|
| **Gemini 3.8 Flash TTS** | Gemini API, *Interactions* endpoint `POST /v1beta/interactions`, key in header `x-goog-api-key` | Free tier; supports Amharic; offers stock voices, so no one's voice is cloned; style instructions in natural language | Stage 4: one WAV per narration line (voice *Charon*) |
| **Gemini 3.8 Flash** (fallback **Flash-Lite**) | Gemini API, `POST /v1beta/models/{model}:generateContent` | Free tier; JSON output mode | Optional `script` stage (drafts a storyboard), never run; transcription and translation in the language test (E16), run with the fallback `gemini-flash-lite-latest` |
| **FLUX.2 klein 4B** | Cloudflare Workers AI REST, `POST /client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-2-klein-4b`, multipart form, `Authorization: Bearer` | Daily free allowance (10,000 neurons); fast (4 fixed steps, about 10 s per image); accepts up to 4 reference images | Stage 1: keyframes and reference sheets |
| **Wan 2.2 TI2V-5B** | Kaggle notebook (T4 GPU) via 🤗 diffusers `WanImageToVideoPipeline`, weights `Wan-AI/Wan2.2-TI2V-5B-Diffusers` | Open weights (Apache 2.0); image-to-video that fits a 16 GB T4 with fp16 and CPU offload | Stage 2: optional 5 s clips per keyframe (**not yet run**) |
| **ACE-Step 1.5** (`acestep-v15-turbo`) | Kaggle notebook, the project's Python API (`AceStepHandler`, `generate_music`) | Open weights; outputs usable commercially; caption, bpm and key control | Stage 3: three score candidates (**not yet run**) |

## Media tooling

### FFmpeg 6.1.1 and ffprobe

- **What:** the industry-standard command-line media toolkit. The build must include **libass**, because subtitles are burned in with the `ass` filter.
- **Why:** every editing operation the brief requires can be expressed as a reproducible filter graph: crossfades (`xfade`), ducking (`sidechaincompress`), loudness normalisation to EBU R128 (`loudnorm`), Ken Burns (`zoompan`), subtitle burn-in (`ass`) and encoding (`libx264`, `aac`).
- **Where:** `shots.py` (segments), `music.py` (placeholder pad, loudness matching), `assemble.py` (mix, render, verification), `radio.py`; `common.ffmpeg()`, `common.probe()` and `common.duration_s()` wrap the binaries.
- **How it interacts:** Python builds filter-graph strings from storyboard values and runs FFmpeg through `subprocess.run(..., check=True)`, so any FFmpeg failure stops the stage with a non-zero exit.

### Fonts

Subtitles and cards use **Noto Sans**. The ASS style names it, and `assemble.font()` looks for the TrueType file in a list of paths, falling back to DejaVu Sans, then Arial, then Pillow's built-in font.

## Build, automation and collaboration

Table: Supporting tools.

| Tool | Version | Role |
|---|---|---|
| GNU Make | 4.3 | One target per stage (`make film`, `make shot SHOT=s03`, `make test`); self-documenting `make help` |
| Git and GitHub | 2.43 | Version control; model outputs are **committed** so that a clone gets cache hits instead of API calls |
| Kaggle Notebooks | — | Free T4 GPU sessions for Wan 2.2 and ACE-Step (manual upload and download) |
| LibreOffice | 24.2 | `make report`: converts the report to PDF and DOCX |
| Google Chrome (headless) and mermaid-cli 11.12 | 158 / 11.12.0 | Build this document and render its diagrams (documentation tooling only) |

## Technology stack summary

Table: The whole stack by layer.

| Layer | Technology |
|---|---|
| Interface | GNU Make targets → `run.py` (argparse) |
| Contract | `storyboard.json` + `schema/storyboard.schema.json` (JSON Schema 2020-12) |
| Orchestration | `run.py` `FILM` list; stages communicate only through the storyboard and files |
| Model clients | `pipeline/providers.py` over `requests` |
| Reliability | `common.call_with_retries`, `common.retry_delay`, `common.parse_wait` |
| Caching | SHA-256 content hashes in file names (`common.canonical_hash`, `common.cache_path`) |
| Media processing | FFmpeg/ffprobe, Pillow, a pure-Python pause compressor |
| Observability | `runs.jsonl` (append-only JSON Lines), `make costs` |
| GPU work | Kaggle notebooks (diffusers Wan 2.2, ACE-Step 1.5) bridged by `kaggle_io.py` |
| Quality gates | pytest (25 tests), `assemble.verify` → `report.json`, GitHub Actions workflow `.github/workflows/tests.yml` (validate, timing, tests on a clean Ubuntu runner) |
| Secrets | `.env` loaded by python-dotenv; git-ignored |

# System Architecture

## Architectural style

The system is a **file-based, stage-oriented batch pipeline** organised around a single declarative contract.

- **No shared state.** Stages never call each other's outputs through memory: they meet only through `storyboard.json` and files on disk.
- **The file system is the cache.** Every generated file's name contains a hash of the inputs that produced it, so "does this output exist?" and "is it up to date?" are the same question.
- **Validate first.** Every stage starts with `load_storyboard()`, so a broken contract stops the run before any model is called.
- **Leaf clients.** External services are reached only through `providers.py`, and every call goes through one retry-and-log wrapper.

@@fig architecture landscape | System architecture. The operator drives the Makefile; `run.py` dispatches to stage modules after validation; the providers module is the only code that talks to hosted models; `common.py` gives every stage hashing, caching, retries, logging and FFmpeg wrappers; the Kaggle GPU stages are bridged by zip files that move by hand.

## Components and responsibilities

Table: Architectural components.

| Component | Files | Responsibility |
|---|---|---|
| Operator interface | `Makefile`, `run.py` | Map human commands to stage functions; run the `film` sequence; pass `--shot`, `--force`, `--zip` |
| Contract | `storyboard.json` | Single source of truth: shots, prompts, seeds, narration (Amharic and English), voice, music, render and mix settings, consent flags, changelog |
| Contract schema | `schema/storyboard.schema.json` | Structural rules: required fields, types, ranges, enums, `additionalProperties: false` everywhere |
| Validator and consent gate | `pipeline/validate.py` | Schema validation plus cross-field rules; refuses a likeness flag that ETHICS.md does not support; prints consent warnings |
| Shared core | `pipeline/common.py` | Paths, `.env` loading, `runs.jsonl` logger, canonical hashing, cache paths and hits, atomic writes, retries, FFmpeg/ffprobe wrappers |
| Model clients | `pipeline/providers.py` | Gemini text (with Flash-Lite fallback), Gemini TTS, Cloudflare FLUX.2 klein; cost metadata per call |
| Stage 4 | `pipeline/narration.py`, `pipeline/audio.py` | TTS per shot, pause compression, the film **timeline** |
| Stage 1 | `pipeline/keyframes.py` | Consent-aware prompt composition, reference sheets, keyframes, contact sheet |
| Stage 2 | `pipeline/shots.py` | Per-shot, per-aspect video segment from a Wan clip or Ken Burns |
| Stage 3 | `pipeline/music.py` | Chosen ACE-Step candidate or a synthesised placeholder, loudness-matched |
| Stage 5 | `pipeline/assemble.py` | Subtitles, end card, DRAFT mark, mix, render, verification report |
| Auxiliary | `radio.py`, `kaggle_io.py`, `costs.py`, `script.py`, `smoke.py` | Radio cut; Kaggle export/import; cost table; storyboard draft; provider smoke test |
| GPU notebooks | `notebooks/*.ipynb` | Wan 2.2 clips and ACE-Step candidates on Kaggle, logging in the same JSON format |
| Storage | `outputs/`, `runs.jsonl` | Content-addressed artefacts; append-only event log |
| Tests | `tests/` | Offline verification with fake providers and real FFmpeg |

## Component interactions

1. **Command dispatch.** `make <target>` runs `.venv/bin/python run.py <command>`. `run.py` looks the command up in its `COMMANDS` table, imports the module with `importlib`, and calls `module.main(command, args)`. `film` iterates over the `FILM` list.
2. **Validation.** Each `main()` calls `load_storyboard(stage=…)`, which raises `SystemExit` with a list of errors and logs a `validation` event with `ok: false`.
3. **Generation.** A stage computes the cache key for each item. On a miss it calls a provider function, which calls `call_with_retries`, which logs every attempt.
4. **File hand-off.** Later stages find earlier outputs by recomputing the same key: `shots.py` calls `keyframes.keyframe_path()` and `narration.timeline()`, and `assemble.py` calls `shots.segment()` and `music.prepare()`. Nothing is passed in memory between commands, so any stage can be run alone.
5. **Logging.** All modules write through `common.log_event()`, which stamps each line with the same `run_id` for a whole `make film` (via the `HERITAGE_RUN_ID` environment variable).

@@fig modules | Module dependency graph, derived from the `import` statements. Every stage module also imports `common` directly; those edges are omitted for readability. There are no cycles: `common` depends on nothing inside the package.

## Data flow between components

Data enters as human-written JSON and leaves as MP4, SRT and JSON reports. In between, every intermediate representation is a file whose name carries its cache key (Chapter 7):

- **Narration:** text → WAV → pause-compressed WAV.
- **Keyframes:** prompt → PNG.
- **Shots:** PNG → MP4 segment, two per shot.
- **Assembly:** WAVs plus score → mixed WAV, then segments plus mix plus subtitles → final MP4.

## External services and integrations

Table: External integrations and their failure behaviour.

| Service | Endpoint / mechanism | Authentication | Failure behaviour |
|---|---|---|---|
| Gemini API (TTS) | `POST https://generativelanguage.googleapis.com/v1beta/interactions` | `x-goog-api-key` header, from `GEMINI_API_KEY` | Retries on 429/5xx with server-hinted waits; fail fast if the wait exceeds 120 s |
| Gemini API (text) | `POST …/v1beta/models/{model}:generateContent` | same | After retries, one fallback to `GEMINI_TEXT_FALLBACK` if the error contains 503 |
| Cloudflare Workers AI | `POST https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}` (multipart) | `Authorization: Bearer` with `CLOUDFLARE_API_TOKEN` | Same retry policy; JSON errors with `success: false` raise `ModelCallError` |
| Kaggle | Manual: upload `kaggle/heritage_job.zip` as a dataset; download `heritage_results_wan.zip` / `heritage_results_music.zip` | Kaggle account (phone-verified) | Notebook logs failed clips as `status: error` and continues; locally, a missing clip falls back to Ken Burns |
| FFmpeg / ffprobe | Local subprocess | — | `check=True`: any error stops the stage |

## Consent gate as an architectural concern

Consent is enforced in four places, so no single oversight can leak a likeness:

1. **The validator.** `likeness_approved: true` is rejected while ETHICS.md says *Pending*.
2. **Prompt composition.** `keyframes.shot_prompt()` uses `no_face_prompt` and omits the character description.
3. **Reference sheets.** `keyframes.make_refs()` skips the character sheet and logs `consent_gate`.
4. **The Kaggle export.** `kaggle_io.export()` appends a hide-face instruction to motion prompts.

Script approval is enforced at render time with the DRAFT overlay.

@@fig consent | The consent gate. Both flags live in the storyboard; the likeness flag can only be turned on once the written consent record in ETHICS.md no longer says *Pending*.

## Observability architecture

`runs.jsonl` is an append-only JSON Lines file. Each line has the same envelope (`ts`, `run_id`, `event`, `stage`) and event-specific fields.

Table: Event types in `runs.jsonl` and their counts at the time of writing (130 lines).

| Event | Written by | Count | Meaning |
|---|---|---|---|
| `model_call` | `call_with_retries`, Kaggle notebooks | 44 | One attempt at a hosted-model request: status, latency, error, cost |
| `cache_hit` | `common.cache_hit` | 27 | A model call that was **not** made because its output already existed |
| `stage_done` | each stage's `main()` | 20 | A stage completed (with its shot list or output) |
| `render` | `shots.segment` | 18 | A segment was rendered by FFmpeg |
| `mix` | `assemble.mix_audio` | 7 | A new mix was produced (loudness before and after) |
| `consent_gate` | `keyframes` | 6 | The gate changed what was generated |
| `validation` | `validate` | 4 | Explicit validation runs |
| `export`, `import` | `kaggle_io` | 2, 0 | Kaggle bridge activity |
| `placeholder`, `smoke_summary` | `music`, `smoke` | 1, 1 | Temp score created; smoke-test summary |

# Building the Project from Scratch

This chapter retells, in order, how the repository was built. The order comes from the git history and from the timestamps in `runs.jsonl` (UTC; commit times are local, UTC+3). Each step says what was built, why it was needed, how it was implemented, and what it enabled next.

Table: Commit history of the main branch.

| Commit | Local time (25 Nov 2026) | Content |
|---|---|---|
| `620edeb` | 15:33 | Step 1: project skeleton, design brief, consent record |
| `9bad017` | 15:49 | Initialise project structure and story notes |
| `1b715f8` | 15:54 | Design brief and story notes, **before any generation** |
| `3882fed` | 16:03 | Step 2: core library (log, hash, retry), providers, smoke test |
| `22b22dd` | 17:58 | Steps 3–5: storyboard contract, five stages, consent gate, Kaggle bridge, tests |
| `56a0295` | 17:58 | Generated outputs and `runs.jsonl`: keyframes, narration, temp score, draft film |
| `265f650` | 17:58 | Docs: README, ARCHITECTURE, DESIGN, EXPERIMENTS, FAILURES, COSTS, ETHICS |
| `19f4e83` | 17:58 | Makefile: quote the interpreter path (repository paths with spaces) |
| `b6e8651` | 18:06 | COSTS: clean-clone `make film` verified (0 model calls, 18 cache hits) |
| `5617003` | 20:51 | Submission preparation: report draft, `make report`, checklist |

Steps 3–5 were committed together, so their internal order below follows code dependencies and the first log line of each stage: narration 14:00 UTC, keyframes 14:14, music 14:17, shots 14:17, assembly 14:21, radio 14:27, Kaggle export 14:28.

## Initial project setup

**What and why.** Before any code, the author wrote the audience, intent and story notes (DESIGN.md §1, `story/notes.md`) and a consent record (ETHICS.md). The brief grades "audience and intent stated before generating", and the consent record decides what the pipeline may generate. Committing these first (`1b715f8`) gives a timestamped proof that design came before generation.

**How.** Plain Markdown files: `DESIGN.md`, `ETHICS.md`, `story/notes.md`, and a `.gitignore` that excludes `.env` from the very first commit.

**Next.** The story notes became the source text for the storyboard; the consent record became an input to the validator (Section 5.2).

## Environment preparation

**What and why.** An isolated Python environment with pinned dependencies, and FFmpeg on the `PATH`.

**How.** The intended command is the Makefile's `setup` target:

@@lines Makefile:11-13

On the author's Ubuntu machine, `python3 -m venv` had created `.venv` **without pip**: the `python3.12-venv` package, which supplies `ensurepip`, was missing, and installing it needs sudo. `import requests` failed inside the venv. The fix was to bootstrap pip into the existing venv with the official PyPA `get-pip.py`, then install the requirements (FAILURES.md F01). The commands below are an equivalent of what was run, not a transcript:

```bash
curl -sSLO https://bootstrap.pypa.io/get-pip.py
.venv/bin/python -I get-pip.py
.venv/bin/python -m pip install -r requirements.txt
```

The same investigation found that the committed smoke-test outputs were **0-byte files** and that there was no `runs.jsonl`: no provider had ever really been called. The smoke test was rerun for real. The lesson recorded is that "an artefact that exists is not evidence that something ran. The log is."

**Next.** With a working interpreter the core library could be written and the providers smoke-tested.

## Repository and folder structure

The final layout separates the contract, code, generated media, documentation and tests:

```text
heritage-short/
├── Makefile                  one target per stage; `make film` runs everything
├── run.py                    CLI entry point (argparse) → pipeline modules
├── storyboard.json           the contract (9 shots, consent, style, voice, music, render, mix)
├── schema/storyboard.schema.json
├── pipeline/                 one module per stage + shared core
│   ├── common.py  providers.py  validate.py  audio.py
│   ├── narration.py  keyframes.py  shots.py  music.py  assemble.py
│   └── radio.py  kaggle_io.py  costs.py  script.py  smoke.py
├── notebooks/                wan_video.ipynb, ace_step_music.ipynb (Kaggle)
├── tests/                    conftest.py, test_storyboard.py, test_pipeline.py
├── outputs/                  generated files, named by content hash
├── runs.jsonl                append-only log of every model call and event
├── story/notes.md            the author's story notes
├── docs/                     report, walkthrough, interview prep, this documentation
└── README.md ARCHITECTURE.md DESIGN.md EXPERIMENTS.md FAILURES.md COSTS.md ETHICS.md SUBMISSION.md
```

`run.py` was first created inside `story/`, from where `python run.py` could not import the `pipeline` package. It was moved to the repository root with `git mv` (F01).

## Dependency installation

Dependencies are pinned to exact versions in `requirements.txt` (Section 2.3) and installed with `make setup`. Only five packages are needed at run time; provider SDKs were deliberately avoided, because one `requests.post` per provider is enough and keeps the retry logic in one place. System dependencies (FFmpeg with libass, Make, a TrueType font) are documented in the README.

## Configuration and environment variables

**What and why.** API keys must never be committed (a brief requirement), and model names must be changeable without code edits.

**How.** `.env.example` documents every variable; the real `.env` is git-ignored. `common.py` loads `.env` once at import time with python-dotenv, and `common.env()` reads a variable or stops with an actionable message:

@@code pipeline/common.py::env

@@lines .env.example:1-11

Model names have defaults in code (`env("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")`), so only the keys are mandatory. Because the model name is part of every cache key, switching models automatically invalidates the affected outputs.

**Run-wide configuration** lives in the storyboard, not in the environment: frame rate, sizes, transition length, mix targets and consent flags are data, validated by the schema and versioned in git.

## Backend implementation: the shared core and providers

The project has no server; its "backend" is the library every stage uses (`pipeline/common.py`) and the model clients (`pipeline/providers.py`), written in step 2 (`3882fed`).

### Event logging

@@code pipeline/common.py::log_event

Every line carries a `run_id` that is generated once per process and exported in `HERITAGE_RUN_ID`, so all six stages of one `make film` share it:

@@code pipeline/common.py::RUN_ID

### Content hashing and the cache

@@code pipeline/common.py::canonical_hash

@@code pipeline/common.py::cache_path

@@code pipeline/common.py::cache_hit

@@code pipeline/common.py::write_atomic

`canonical_hash` serialises with sorted keys and fixed separators, so two dictionaries with the same content always hash the same, regardless of key order. `write_atomic` guarantees a crash never leaves a half-written file that a later run would treat as a valid cache entry.

### Retries

`call_with_retries` wraps exactly **one** request (the function `fn`), logs every attempt, classifies errors and decides whether and how long to wait. Its behaviour is detailed in Section 5.9.

@@code pipeline/common.py::call_with_retries

### Provider clients

Each provider function builds one request inside a local `once()` closure, returns `(result, meta)` with cost metadata, and hands `once` to `call_with_retries`. The Cloudflare client shows the pattern, including the multipart trick (`(None, value)` tuples force `multipart/form-data` even without files) and the neuron-based cost estimate:

@@code pipeline/providers.py::cloudflare_image

**Smoke test.** `python run.py smoke` calls FFmpeg, Gemini text, Gemini TTS (an Amharic sentence) and FLUX.2 klein once each and prints a table. The first real run (13:49 UTC) found:

- FFmpeg, TTS and Cloudflare working.
- **Gemini 3.8 Flash text failing 3 times with HTTP 503 "high demand"**, at 23.8–35.9 s per attempt.
- The image prompt "a clay coffee pot (jebena)" drawn as a plain vase (E01).

The 503s led to the Flash-Lite fallback in `gemini_text`.

## Frontend implementation

Not applicable. The project has no graphical or web interface; the operator uses Make targets and `run.py`. The "presentation layer" of the product is the film itself, plus human-readable console output and Markdown reports.

## Core pipeline implementation

Step 3 was the **contract**: `schema/storyboard.schema.json` (JSON Schema 2020-12 with `additionalProperties: false` at every level) and `pipeline/validate.py` (cross-field rules). The storyboard itself, nine shots in version 1, was drafted by the coding agent from the story notes and design brief; its first changelog line says so.

Step 4 was the **five stages**, built in dependency order:

1. **Narration first** (`narration.py`), because its durations define the timeline. The first full take was 77.4 s of speech and made the film 92.2 s. That produced the pause compressor (`audio.py`) and the `voice.max_pause_s` setting (E02–E04).
2. **Keyframes** (`keyframes.py`), with consent-aware prompt composition. Experiments here led to describing the coffee pot by its shape, rewriting the s04 "no face" prompt that still showed a profile (E05, E06), and turning the style reference image off (E07).
3. **Music** (`music.py`): the ACE-Step path plus a synthesised placeholder, so the film could be assembled before any GPU work.
4. **Shots** (`shots.py`): Ken Burns over every keyframe, with a hook for Wan clips.
5. **Assembly** (`assemble.py`): mix, subtitles, render, verification. Iterating on it produced the balanced subtitle wrapping (E08), the pre-limiter that makes −14 LUFS reachable under the true-peak ceiling (E09), and a measurement that the ducking works (E10).

Step 5 was the **consent gate** across validator, prompts, references and the Kaggle export, the **Kaggle bridge** with its two notebooks, the **radio cut**, the **cost summariser** and the **tests**.

## API and service integration

Table: How each external service was integrated and what was learned.

| Service | Integration detail | Lesson from the logs |
|---|---|---|
| Gemini TTS | Interactions API; audio found by a recursive search for a base64 `data` field whose type mentions "audio"; raw PCM wrapped into a 24 kHz mono WAV if the response is not already RIFF | Free tier: 3 requests/min and about 10/day. A 2–4 s backoff burned all retries against a "retry in 39s" limit (F03); a "retry in 17h50m8s" message was not parsed and wasted about 10 minutes (F04) |
| Gemini text | `generateContent` with optional JSON mode; thought parts filtered out | Persistent 503 overload; fallback to Flash-Lite added (F02) |
| Cloudflare FLUX.2 klein | Multipart form; reference images shrunk below 512 px (`_small_png`); JPEG or PNG responses normalised to PNG | 1024×1024 = 4 output tiles ≈ 104 neurons, so about 95 images/day free. A reference image is treated as content to edit, not as a style (E07) |
| Kaggle | Zip export and import; notebooks log in the same JSON format with `gpu_minutes` | Notebooks prepared but not yet run (no GPU locally) |

## Testing and debugging

Tests were written alongside the stages with **fake providers**, so the suite never spends quota. FFmpeg is real, so filter graphs are genuinely exercised. Debugging was driven by `runs.jsonl` and recorded in FAILURES.md:

Table: Failures met during the build, and their fixes.

| ID | Failure | Fix |
|---|---|---|
| F01 | venv without pip; smoke outputs were 0-byte files; `run.py` in the wrong folder | `get-pip.py`; rerun smoke; `git mv run.py .` |
| F02 | Gemini Flash 503 on every attempt | Flash-Lite fallback |
| F03 | TTS 429 at 3 RPM; backoff too short | `retry_delay` honours `Retry-After` / "retry in Ns" |
| F04 | TTS daily quota; wait string `17h50m8s` not parsed | `parse_wait` handles h/m/s; waits over 120 s fail fast |
| F05 | Narration made the film 92 s | `compress_pauses`, 0.45 s cap → 84.4 s |
| F06 | "Jebena" drawn as a vase, then as a pot with a pipe | Describe the shape, not the name |
| F07 | "No face" prompt still showed a profile | "Directly behind, her back to the camera"; manual check of every character keyframe |
| F08 | Style reference made keyframes worse | `use_style_reference: false` |
| F09 | `aevalsrc` comma parsing; `ass=` filter and paths with spaces; orphan subtitle word | Quoted expression; run FFmpeg with `cwd`; balanced wrapping |
| F11 | Text-model fallback named a model that does not exist (HTTP 404), found when 3.8 Flash was overloaded during E16 | Checked `ListModels`; fallback is now `gemini-flash-lite-latest` |
| F10 | Kaggle notebooks, checked against library source before the first GPU run: ACE-Step ignored seeds, init failures did not raise, `pip install -e` cannot resolve its deps | `use_random_seed=False`; check the `ok` flag; official `uv sync`; Wan pinned to diffusers 0.43.0 with `expand_timesteps=True` |

## Final execution

`make film` on the working copy produced both exports and a passing `report.json`. As a reproducibility test, a **fresh clone without `.env`** ran `make film`: exit status 0 in 7 min 40 s, **0 `model_call` lines and 18 `cache_hit` lines** added to `runs.jsonl` (9 narration + 9 keyframes), segments re-rendered by FFmpeg, both exports verified (COSTS.md, commit `b6e8651`). The console output of that run is reproduced in Section 8.6.

# Complete End-to-End Pipeline Explanation

## The pipeline at a glance

`make film` executes `run.py film`, which runs `["validate", "narration", "keyframes", "shots", "music", "assemble"]` in order in one Python process. Each command loads and validates the storyboard again, so any stage can also be run alone with exactly the same guarantees.

@@lines run.py:30-58

@@fig pipeline | End-to-end pipeline of `make film`. Each band is one command; diamonds are the decisions that make the pipeline incremental (cache checks), consent-aware (prompt choice), resilient (Wan clip or Ken Burns, ACE-Step score or placeholder) and self-checking (verification). Green boxes are the only two places that call a hosted model.

The rest of this chapter describes each stage with the same headings: purpose, input, processing, functions, output, hand-off, and errors and validation.

## Stage 0 · Validation

**Purpose.** Stop a broken or non-consenting storyboard before any model call or render.

**Input.** `storyboard.json`, `schema/storyboard.schema.json`, and the consent table in `ETHICS.md`.

**Processing.**

1. Validate against the schema with `Draft202012Validator`; errors are sorted by JSON path and shortened.
2. If the structure is valid, apply the cross-field rules:
   - shot ids are unique;
   - planned length (shot durations + end card) is within 60–90 s;
   - every character shot has a `no_face_prompt`;
   - every reference's `chosen_seed` is one of its seeds, and so is `music.chosen_seed`;
   - `likeness_approved` is not set while ETHICS.md says *Pending*.
3. Emit warnings for subtitles over 120 characters, missing likeness consent, and an unapproved script.

@@code pipeline/validate.py::check

**Output.** None on success (the parsed board is returned to the caller). The `validate` command logs a `validation` event with the version, shot count and planned length.

**Hand-off.** Every stage receives the validated dictionary from `load_storyboard()`.

**Errors and validation.** Any error raises `SystemExit("storyboard is invalid: …")` and logs `validation` with `ok: false`. Because the check runs at the top of every stage, nothing downstream can run on an invalid contract.

## Stage 4 · Narration

**Purpose.** Produce one Amharic voice file per shot with a stock Gemini voice, and derive the film's timeline from their lengths.

**Input.** For each shot, `narration.am`; the global `voice.voice` ("Charon"), `voice.style` and `voice.max_pause_s` (0.45); and the TTS model name.

**Processing.**

1. `narration_key` hashes text, voice, style and model.
2. If `outputs/narration/raw/<id>_<key12>.wav` exists, log `cache_hit`. Otherwise call `gemini_tts`, which returns WAV bytes, and write them atomically.
3. Unless it already exists, create the processed file `outputs/narration/<id>_<key12>_p450.wav` with `compress_pauses`. That function:
   - analyses 20 ms RMS frames against −40 dBFS;
   - shortens interior silences longer than `max_pause_s` to exactly that length, keeping half on each side of the cut;
   - trims leading and trailing silence to 0.1 s.

@@code pipeline/narration.py::generate

The pause compressor is deterministic standard-library Python:

@@code pipeline/audio.py::compress_pauses

**Output.** Raw WAVs (24 kHz mono 16-bit, the model's output, kept untouched) and processed WAVs used by every later stage.

**Hand-off: the timeline.** `timeline()` turns narration lengths into shot timing. Each shot lasts `max(planned duration, lead_in_s + narration + 0.6 s)`, so a line is never cut off and is followed by at least 0.6 s of air:

@@code pipeline/narration.py::timeline

Table: The timeline of the current film (`make timing`). Six of nine shots were stretched to fit their line.

| Shot | Planned (s) | Narration (s) | Used (s) | Note |
|---|---|---|---|---|
| s01 | 7 | 5.86 | 7.00 | |
| s02 | 8 | 8.22 | 9.22 | stretched to fit the line |
| s03 | 7 | 6.43 | 7.43 | stretched |
| s04 | 8 | 8.36 | 9.36 | stretched |
| s05 | 8 | 5.97 | 8.00 | |
| s06 | 8 | 3.67 | 8.00 | |
| s07 | 8 | 9.33 | 10.33 | stretched |
| s08 | 8 | 10.29 | 11.29 | stretched |
| s09 | 8 | 9.78 | 10.78 | stretched |
| **Total** | 70 + 3 s end card | 67.91 | 81.41 + 3 = **84.41** | within 60–90 s |

**Errors and validation.** TTS errors go through the retry policy (Section 5.9); a daily-quota 429 stops the run with "quota exhausted … rerun later", and outputs already cached are kept. `compress_pauses` rejects anything but 16-bit mono WAV. `timeline(require_audio=True)` stops with "no narration for the current text; run `make narration`" if a processed file is missing.

**Why the processed file has a different name pattern.** Changing `max_pause_s` changes only the `_p<ms>` suffix: no TTS call, just a new deterministic file. A test asserts exactly this (`test_pause_setting_changes_no_model_call`).

## Stage 1 · Keyframes

**Purpose.** One 1024×1024 still per shot, in a consistent style, that respects consent.

**Input.** Per shot: `image_prompt` or `no_face_prompt`, `seed`, `character`. Globally: `style.style_block`, `style.character_block`, `style.use_style_reference`, `style.image_size`, `references`, `consent.likeness_approved`.

**Processing.**

1. **Prompt composition.**
   - Shots that show the mother: the `image_prompt` and the character description, but only with likeness consent. Without consent, the `no_face_prompt` replaces the `image_prompt` and the character description is dropped.
   - Every prompt ends with the shared style block.

@@code pipeline/keyframes.py::shot_prompt

2. **References.**
   - The chosen style sheet is attached only if `use_style_reference` is true (currently false, after E07).
   - The chosen character sheet is attached only with consent. If consent is recorded but no sheet has been chosen, generation stops with instructions.
3. **Cache key.** `keyframe_key` hashes the final prompt, seed, size, model and the SHA-256 of each reference image. Replacing a reference image therefore regenerates exactly the keyframes that used it.

@@code pipeline/keyframes.py::keyframe_key

4. **Generation.** On a miss: log `consent_gate` if the no-face variant is used, call `cloudflare_image`, convert to PNG, write atomically.
5. **Review aid.** When all current keyframes exist, `contact_sheet()` tiles them into `contact_sheet.jpg`.

**Output.** `outputs/keyframes/<id>_<key12>.png` and `contact_sheet.jpg`. Reference candidates are made separately with `make refs` and saved as `outputs/references/<name>_seed<N>_<key12>.png`; the character sheet is skipped without consent.

**Hand-off.** Later stages call `keyframe_path(board, shot)`, which recomputes the key, so they always pick up the keyframe for the *current* prompt.

**Errors and validation.** Provider errors go through the retry policy; Cloudflare JSON errors (`success: false`) and responses without an image raise `ModelCallError`. A chosen reference seed with no image stops with "run `make refs`".

## Stage 2 · Moving shots

**Purpose.** A video segment per shot and per aspect ratio, of exactly the length the timeline needs plus the crossfade overlap.

**Input.** Timeline rows; per shot `video` ("kenburns" or "wan"), `kenburns` (in, out, left, right, up, down); `render.fps`, `render.sizes`, `render.transition_s`; the keyframe, and any imported Wan clip.

**Processing.**

1. **Source selection.** If `video == "wan"` and `outputs/shots/wan/<id>_<keyframe_key12>.mp4` exists, use the clip. Otherwise use the keyframe. Because the clip's name embeds the keyframe key, a clip made from an old keyframe is ignored automatically.
2. **Length.** `dur + transition_s`. The extra 0.5 s is the tail that the next crossfade overlaps, so crossfades do not shorten the film.
3. **Ken Burns filter.**
   - Crop the square keyframe to the output aspect ratio and scale it to 3× the output size (`OVERSCALE`), which hides `zoompan`'s whole-pixel rounding jitter.
   - Zoom or pan by 12 % (`ZOOM = 1.12`) with a cosine ease-in-out: `0.5 − 0.5·cos(π·progress)`.

@@code pipeline/shots.py::kenburns_filter

4. **Wan clip filter.** Cover-crop to the aspect, slow down by at most 1.6× (`setpts`), then hold the last frame (`tpad`) and trim to length.
5. **Cache.** The key hashes the source file, method, direction, length, size, fps, zoom and a manual version number (`"v": 2`). If the file exists it is reused silently; otherwise it is rendered with `libx264 -crf 18 -preset veryfast` and a `render` event is logged.

@@code pipeline/shots.py::segment

**Output.** `outputs/shots/vertical/<id>_<key12>.mp4` and `outputs/shots/horizontal/<id>_<key12>.mp4`. These are derived files, git-ignored and rebuilt on a clean clone.

**Hand-off.** `assemble.render()` calls `segment()` again for each row and aspect; it returns the cached path instantly.

**Errors and validation.** A missing keyframe stops with "keyframe missing … run `make keyframes`". FFmpeg failures raise `CalledProcessError`.

## Stage 3 · Music

**Purpose.** Provide one score file, loudness-matched to −20 LUFS, for the mix.

**Input.** The `music` block: caption, bpm 68, key A minor, duration 90 s, seeds [11, 22, 33] and `chosen_seed`; plus any imported candidates in `outputs/music/candidates/seed_<N>.{wav,flac,mp3}`.

**Processing.**

- **If `chosen_seed` is set:** find that candidate, hash it, and `match_loudness()` it to −20 LUFS (a linear gain computed from FFmpeg's loudnorm measurement). The result is `score_seed<N>_<key>.wav`.
- **Otherwise:** synthesise a **placeholder**, a temp track and not AI-generated:
  - an A minor – F – C – G pad from three sine voices per chord, built with FFmpeg's `aevalsrc`;
  - each chord lasts two bars at the storyboard tempo and swells in and out;
  - the pad is low-passed, given a light echo and a 2 s fade-in, then loudness-matched.

  It is logged as `placeholder` with the note "FFmpeg pad, not a model call".

@@code pipeline/music.py::prepare

**Output.** `outputs/music/placeholder_<key>.wav` (current) or `outputs/music/score_seed<N>_<key>.wav`.

**Hand-off.** `assemble.mix_audio()` calls `prepare()` directly and receives `(path, source)`. The `source` string ("placeholder" or "ace-step seed N") is recorded in the mix statistics and in `report.json`, so the release state is never ambiguous.

**Errors and validation.** A `chosen_seed` without a file stops with instructions to run the Kaggle notebook and import. Candidates that are present but not yet chosen are announced.

## Stage 5 · Assembly

**Purpose.** Produce the two finished, verified exports and the subtitle file. No model is called.

**Input.** Timeline rows, processed narration, the score, segments, `render`, `mix`, `consent`, and `narration.en` for subtitles.

### Audio mix

1. Each narration line is loudness-matched to −20 LUFS and delayed to `start + lead_in_s`.
2. The lines are summed (`amix normalize=0`), padded and trimmed to the film length, then split into a *voice* copy and a *key* copy.
3. The score is looped, trimmed, faded in over 2 s and out over 3.5 s, and set to `music_gain_db` (−8 dB).
4. `sidechaincompress` ducks the music whenever the key (the voice) is present: threshold 0.02, ratio 6, attack 300 ms, release 1500 ms.
5. Voice and ducked music are summed, peak-limited at −10 dBFS (`alimiter`), and normalised with **two-pass linear `loudnorm`** to −14 LUFS and −1.5 dBTP.

The mix is cached as `outputs/final/mix_<key>.wav` with a `.json` of loudness before and after.

@@fig audiomix | Audio mix filter graph built by `assemble.mix_audio()`. All values come from the storyboard's `mix` and `render` blocks. The two loudnorm passes are separate FFmpeg runs: the first measures, the second applies the measured values in linear mode.

@@code pipeline/assemble.py::mix_audio

Measured effect of the ducking (EXPERIMENTS.md E10): music RMS under speech fell from −30.2 dBFS to **−43.2 dBFS (−13 dB)**, while in pauses it stayed at −31.3 dBFS. Measured effect of the pre-limiter (E09): without it, linear loudnorm under a −1.5 dBTP ceiling reached only −15.03 LUFS; with a −10 dBFS pre-limiter the exports measure **−14.04 LUFS and −1.76 dBTP**.

### Subtitles

`cues()` turns each shot's English line into one or more cues of at most two lines:

- Wrapping uses `balanced_wrap()`: the fewest cues possible, with even line lengths, so no single orphan word is left on a cue (E08).
- Line width is 36 characters for vertical and 42 for horizontal and SRT.
- When a line needs several cues, its speech time is split between them in proportion to their character counts.
- Cues start at `start + lead_in_s`.

`write_ass()` writes an ASS file whose `PlayResX/Y` equal the video size, so font size and margins are in real pixels: 48 px text with a 420 px bottom margin on vertical, keeping clear of platform buttons. `write_srt()` writes `subtitles_en.srt` for upload.

@@code pipeline/assemble.py::balanced_wrap

### Picture and export

@@fig video | Picture chain built by `assemble.render()`, run once per aspect ratio.

- The end card and the DRAFT mark are drawn with **Pillow**, so FFmpeg filters never need font paths.
- The video graph:
  1. normalises every input (timebase, fps, size, SAR, pixel format);
  2. chains `xfade` transitions at cumulative offsets, with a final crossfade into the end card;
  3. fades in over 0.8 s and out over the last 1 s;
  4. burns in the ASS subtitles;
  5. overlays the DRAFT mark while `script_approved` is false.
- Encoding is H.264 (CRF 20, preset medium) plus AAC 192 kbit/s, with `+faststart` and a metadata comment disclosing the AI models.
- FFmpeg runs with its working directory set to `outputs/tmp`, so the `ass=` filter gets a bare file name. The repository path contains spaces, which the filter's argument parser does not tolerate.

@@code pipeline/assemble.py::render

### Verification

`verify()` probes each export and measures its loudness again, then records six checks:

@@code pipeline/assemble.py::verify

**Output.** `outputs/final/the_silent_language_of_a_mother_s_love_vertical.mp4` and `…_horizontal.mp4`, `subtitles_en.srt`, and `report.json`.

**Errors and validation.**

- `build()` refuses to render if the computed film length is outside 60–90 s, and points to `make timing`.
- `main()` exits non-zero if any check fails.
- It also prints a reminder while the score is still the placeholder or the DRAFT mark is on.

## Supporting flows

### The radio cut

`make radio` reuses the same timeline and `mix_audio()` and renders a black 1280×720 video with the horizontal subtitles, giving `outputs/radio/radio_cut.mp4`. It is the cheapest prototype of the film, made for the first audience test (DESIGN.md §4).

### The Kaggle bridge


`kaggle_io.export()` does the following:

- copies the current keyframes;
- writes `jobs.json`, with shots marked `"wan"` first so that a short GPU session does the important ones;
- applies the consent gate to motion prompts;
- includes the Wan parameters: `Wan-AI/Wan2.2-TI2V-5B-Diffusers`, maximum area 480×832, 121 frames at 24 fps, 30 steps, guidance 5.0, and a negative prompt.

`import_results()` moves clips and music candidates into place and appends only log lines not already present, so importing twice is harmless (tested).

@@fig kaggle landscape | Kaggle bridge for the GPU stages. The zip files are moved by hand (the author chose manual upload). The notebooks log in the same JSON format as the local pipeline, so imported GPU calls appear in `runs.jsonl` and in the cost table. This flow is implemented but has not been executed yet.

## Error handling across the pipeline

@@fig retry | `call_with_retries` and `retry_delay`. Every attempt is logged, successful or not. A 429 that asks for more than 120 s is a daily quota: the run stops immediately, keeping every cached output, instead of sleeping for hours.

@@code pipeline/common.py::retry_delay

@@code pipeline/common.py::parse_wait

Table: Error-handling strategies, by layer.

| Layer | Strategy |
|---|---|
| Contract | Schema + cross-field validation at the start of every stage; `SystemExit` with a readable list |
| Hosted models | Up to 4 attempts on 429/5xx, connection errors and timeouts; server-hinted waits; fail fast on daily quotas; 4xx not retried; every attempt logged |
| Overload | Gemini text falls back once to Flash-Lite on a 503 |
| Missing GPU results | Ken Burns instead of a Wan clip; placeholder pad instead of an ACE-Step score |
| Partial writes | `write_atomic` (`.part` then rename) for model outputs and processed narration |
| Media | FFmpeg run with `check=True`; post-render verification with non-zero exit on failure |
| Consent | Validator refusal; no-face prompts; DRAFT overlay |

# Codebase and Implementation Walkthrough

## Directory structure and responsibilities

Table: Top-level files and folders, and what each one is responsible for.

| Path | Responsibility |
|---|---|
| `run.py` | The single entry point. Maps 14 commands, plus `film`, to modules; parses `--shot`, `--force`, `--zip` |
| `Makefile` | Human-friendly targets. `make shot SHOT=s03` chains validate → narration → keyframes → shots → assemble for one shot |
| `storyboard.json` | The film as data; the only file a director edits to change the film |
| `schema/storyboard.schema.json` | The structure the storyboard must satisfy; the same schema is given to Gemini by the `script` stage |
| `pipeline/` | All implementation code (Section 6.2) |
| `notebooks/` | GPU notebooks for Kaggle; self-contained, log in the pipeline's format |
| `tests/` | Offline test suite (Chapter 9) |
| `outputs/` | Every generated artefact, named by content hash. Model outputs are committed; FFmpeg-derived files are ignored (Section 7.5) |
| `runs.jsonl` | Append-only audit log |
| `kaggle/` | Export staging (`job/`, `heritage_job.zip`); git-ignored |
| `story/notes.md` | The author's story notes, the only source of facts about the mother |
| Markdown documents | README (use), ARCHITECTURE (design), DESIGN (audience), EXPERIMENTS, FAILURES, COSTS, ETHICS, SUBMISSION |
| `docs/` | Report draft and exporter, walkthrough plan, post notes, interview preparation, and `technical/` (this document's source) |

## Module-by-module walkthrough

### `pipeline/common.py`: the shared core

The foundation every other module imports.

- **Paths:** `ROOT`, `OUTPUTS`, `RUNS_LOG`, `STORYBOARD`.
- **Logging:** `log_event`, `RUN_ID`.
- **Hashing:** `canonical_hash`, `file_hash`.
- **Cache:** `cache_path`, `cache_hit`, `write_atomic`, `out_dir`, `rel`.
- **Reliability:** `call_with_retries`, `retry_delay`, `parse_wait`, `check_http`, `ModelCallError`, `MAX_RETRY_WAIT_S = 120`.
- **FFmpeg:** `ffmpeg`, `probe`, `duration_s`.

One design rule matters for testability: stages must read `common.OUTPUTS` and `common.RUNS_LOG` **at call time** (`from . import common`, then `common.OUTPUTS`), never via `from .common import OUTPUTS`. That way the test fixture can redirect them to a temporary folder.

@@code pipeline/common.py::check_http

`check_http` attaches the first 300 characters of the response body to the exception, so the log records the provider's real reason (for example the "retry in 39s" text that `parse_wait` needs).

### `pipeline/providers.py`: model clients

Three public functions, each making one *logical* call through `call_with_retries`:

- `gemini_text(prompt, …)` tries the primary model, then falls back once to `GEMINI_TEXT_FALLBACK` if the final error mentions 503.
- `gemini_tts(text, style, voice, …)` posts to the Interactions API and returns WAV bytes. `_find_audio_b64` walks the JSON response recursively, so small changes in response nesting do not break the client. `_pcm_to_wav` wraps raw PCM in a WAV header.
- `cloudflare_image(prompt, width, height, seed, refs, …)` sends a multipart request with up to four reference images, accepts image or JSON responses, and estimates neurons and list-price USD.

@@code pipeline/providers.py::gemini_tts

### `pipeline/validate.py`: contract enforcement

`check()` returns `(errors, warnings)`; `load_storyboard()` prints warnings and raises on errors; `planned_length()` sums shot durations plus the end card. `_ethics_still_pending()` reads ETHICS.md and returns true if any table row mentioning "mother" contains "pending":

@@code pipeline/validate.py::_ethics_still_pending

### `pipeline/narration.py` and `pipeline/audio.py`

Narration owns two concepts: the TTS stage (`narration_key`, `raw_path`, `narration_path`, `generate`) and the **timeline** (`timeline`, `film_length`). The `timing` command prints planned against used durations without rendering anything. `audio.compress_pauses` is the only signal-processing code written in Python; it is described in Section 5.3.

### `pipeline/keyframes.py`

- **Reference sheets:** `ref_prompt`, `ref_key`, `ref_path`, `chosen_ref`, `make_refs`.
- **Consent-aware composition:** `face_allowed`, `shot_prompt`, `shot_refs`.
- **Caching:** `keyframe_key`, `keyframe_path`, `generate`.
- **Review:** `contact_sheet`.
- **Normalisation:** `to_png`.

### `pipeline/shots.py`

`wan_clip` finds a clip for the current keyframe; `kenburns_filter` and `clip_filter` build FFmpeg filter strings; `segment` renders and caches one segment.

@@code pipeline/shots.py::clip_filter

### `pipeline/music.py`

- `measure_lufs` parses the JSON block that FFmpeg's `loudnorm` prints on stderr.
- `match_loudness` applies a linear gain to reach a target.
- `candidate_path` finds imported candidates.
- `placeholder` synthesises the temp pad.
- `prepare` chooses between a candidate and the placeholder.

@@code pipeline/music.py::measure_lufs

### `pipeline/assemble.py`

- **Subtitles:** `cues`, `balanced_wrap`, `ts`, `write_srt`, `write_ass`.
- **Still cards:** `font`, `end_card`, `draft_mark`.
- **Audio:** `limiter`, `mix_audio`.
- **Picture:** `render`.
- **Quality gate:** `verify`.
- **Orchestration:** `build`, `main`.

`build()` is the function the end-to-end test calls directly:

@@code pipeline/assemble.py::build

### Auxiliary modules

Table: Auxiliary modules.

| Module | Key functions | What it does |
|---|---|---|
| `radio.py` | `main` | Radio cut: same timeline and mix on black, with subtitles |
| `kaggle_io.py` | `export`, `import_results` | Zip jobs for Kaggle; bring back clips, music and log lines |
| `costs.py` | `summarise`, `table`, `main` | Groups `runs.jsonl` by stage and model; rewrites the table between `<!-- costs:start -->` and `<!-- costs:end -->` in COSTS.md |
| `script.py` | `main` | Prompts Gemini with DESIGN.md, the notes and the schema; writes `storyboard.draft.json` (never overwrites `storyboard.json`) and validates it. Not yet executed |
| `smoke.py` | `main` | One call per provider plus an FFmpeg check; prints a status table |
| `langtest.py` | `run`, `cer`, `fold_homophones`, `non_script_letters` | E16: transcribes TTS audio back with Gemini and scores it by character error rate; Ethiopic homophone letters can be folded; cached in `outputs/langtest/` |

@@code pipeline/costs.py::summarise

### The notebooks

Both notebooks:

- locate `jobs.json` under `/kaggle/input`;
- write results to `/kaggle/working/results`;
- log each attempt with the same fields as `common.log_event`, plus `gpu` and `cost.gpu_minutes`;
- zip everything into `heritage_results_wan.zip` or `heritage_results_music.zip`.

The Wan notebook:

- pins diffusers 0.43.0 and loads `WanImageToVideoPipeline` with `expand_timesteps=True`, the Wan 2.2 TI2V mode (checked in the library source);
- loads the VAE in fp32 and the pipeline in fp16 with `enable_model_cpu_offload()` to fit a 16 GB T4;
- by default animates only the non-character shots s01, s02, s08 and s09, because image-to-video could turn the mother's face to the camera while consent is pending;
- resizes each keyframe to the model's patch grid under `max_area`;
- rejects clips with black or NaN frames (a float16 risk on a T4);
- skips clips that already exist, so a timed-out session can be resumed;
- logs exceptions (out-of-memory, NaN output) as `status: error` and moves on.

The ACE-Step notebook:

- installs ACE-Step with its official `uv sync` into `/tmp`, isolated from Kaggle's packages and outside the 20 GB output limit;
- runs a generation script inside that environment, which initialises `AceStepHandler` with `acestep-v15-turbo` and checks the returned `ok` flag;
- generates one instrumental per seed with 8 inference steps, without the LM planner, and with `use_random_seed=False` so the seeds are honoured (FAILURES F10).

Neither notebook has been run yet.

## How modules depend on and communicate with each other

Imports point one way: stage modules → `validate` and `providers` → `common` (Figure 3.2). At run time, modules communicate in three ways:

1. **Function calls for derived knowledge.** `shots` asks `keyframes` for the current keyframe path and `narration` for the timeline; `assemble` asks `shots`, `music` and `narration`.
2. **Files on disk for artefacts.** No image, audio or video is passed in memory between commands.
3. **The log for history.** Nothing reads `runs.jsonl` at run time except `costs.py` and the Kaggle import deduplication.

Because every cross-stage lookup recomputes a hash from the current storyboard, a stage can never pick up a stale artefact from an earlier version of a shot.

# Data Flow and Processing

## How data enters the system

Table: Inputs to the pipeline.

| Input | Format | Author | Validated by |
|---|---|---|---|
| `storyboard.json` | JSON | Director (the author; v1 drafted with the coding agent) | JSON Schema + `validate.check` |
| `ETHICS.md` consent table | Markdown table | Author | `_ethics_still_pending` (consent gate) |
| `.env` | KEY=value | Operator | `common.env` (presence) |
| Kaggle results zip | ZIP of MP4, WAV and JSONL | Notebooks | `import_results` (by path pattern) |
| `story/notes.md`, `DESIGN.md` | Markdown | Author | Used only by the optional `script` stage |

## The storyboard contract

Table: Top-level blocks of `storyboard.json` and the stages that read them.

| Block | Content | Read by |
|---|---|---|
| `title`, `language` (`"am"`), `version`, `logline`, `changelog` | Identity and history; `version` is bumped when audience feedback changes the film | assemble (title → file name), report |
| `consent` | `likeness_approved`, `script_approved`, `note` | validate, keyframes, kaggle_io, assemble |
| `style` | `style_block`, `character_block`, `use_style_reference`, `image_size` | keyframes |
| `references` | `style` / `character`: prompt, candidate seeds, `chosen_seed` | keyframes (`make refs`) |
| `voice` | stock voice name, style instruction, `max_pause_s` | narration |
| `music` | caption, bpm, key, duration, seeds, `chosen_seed`, `choice_reason` | music, kaggle_io |
| `render` | fps, `lead_in_s`, `transition_s`, `end_card_s`, `end_card_lines`, `sizes` | narration (timeline), shots, assemble |
| `mix` | music gain, ducking parameters, pre-limiter, loudness targets | assemble |
| `shots[]` (8–12) | id, duration, reason, shot size, character, prompts, seed, narration (am/en), music cue, Ken Burns direction, video source | all stages |

One shot, exactly as stored (the character shot s04, which uses its `no_face_prompt` until consent):

@@json storyboard.json::shots.3

The `mix` block:

@@json storyboard.json::mix

## Validation and transformation

Data is transformed in a fixed sequence of pure or cached steps:

1. **JSON → validated dictionary.** Schema and cross-field checks (Section 5.2).
2. **Dictionary → prompts.** `shot_prompt` composes prompt + optional character block + style block.
3. **Inputs → cache keys.** `canonical_hash` over the exact inputs of each artefact (Table 7.3).
4. **Text → audio → trimmed audio.** TTS, then `compress_pauses`.
5. **Audio durations → timeline rows.** `{id, start, dur, narration, narr_s, shot}`, an in-memory representation recomputed by each stage that needs it.
6. **Timeline + text → subtitle cues.** `(start, end, [line1, line2])` tuples, rendered as ASS (per aspect, pixel-exact) and SRT.
7. **Timeline + files → FFmpeg filter graphs.** Strings built from storyboard values.
8. **Exports → verification report.** ffprobe JSON and loudnorm measurements → `report.json`.

@@fig dataflow | Data flow from human-authored inputs, through cached intermediate artefacts, to the final outputs. Solid arrows are implemented and exercised; the dotted arrow is the optional `script` stage, which has not been run.

## Intermediate representations and cache keys

Table: Every cached artefact, its location, and the inputs in its key.

| Artefact | Path pattern | Key inputs | Producer |
|---|---|---|---|
| Raw narration | `outputs/narration/raw/<id>_<k12>.wav` | Amharic text, voice, style, TTS model | Gemini TTS |
| Processed narration | `outputs/narration/<id>_<k12>_p<ms>.wav` | the above + `max_pause_s` (in the suffix) | `compress_pauses` |
| Reference candidate | `outputs/references/<name>_seed<N>_<k12>.png` | prompt (+ character and style blocks), seed, size, model | FLUX.2 klein |
| Keyframe | `outputs/keyframes/<id>_<k12>.png` | final prompt, seed, size, model, SHA-256 of each reference | FLUX.2 klein |
| Wan clip (imported) | `outputs/shots/wan/<id>_<keyframe k12>.mp4` | named after the keyframe key | Kaggle notebook |
| Segment | `outputs/shots/<aspect>/<id>_<k12>.mp4` | source file hash, method, direction, length, size, fps, zoom, version | FFmpeg |
| Placeholder score | `outputs/music/placeholder_<k12>.wav` | bpm, chords, duration | FFmpeg |
| Chosen score | `outputs/music/score_seed<N>_<k12>.wav` | candidate file hash, −20 LUFS target | FFmpeg |
| Mix | `outputs/final/mix_<k12>.wav` + `.json` | hash and start of every narration file, score hash, mix block, lead-in, total length | FFmpeg |

A single `runs.jsonl` line shows what the log records for each model call (a real keyframe call; no secrets are ever included):

```json
{"ts": "2026-11-25T14:33:32.262+00:00", "run_id": "20261125T143324Z-2cb176",
 "event": "model_call", "stage": "keyframes", "shot": "s05", "provider": "cloudflare",
 "model": "@cf/black-forest-labs/flux-2-klein-4b",
 "params": {"width": 1024, "height": 1024, "steps": 4, "refs": 1, "prompt_chars": 428},
 "seed": 105, "cache_key": "09b7dd26d90e7eb2bf8272d7d5fc5cdb6f4088c74451d948c83a47495c8005b3",
 "output": "outputs/keyframes/s05_09b7dd26d90e.png", "attempt": 1, "status": "ok",
 "latency_s": 7.368,
 "cost": {"neurons_est": 109.57, "usd_list_est": 0.001205, "tier": "free (10,000 neurons/day)"}}
```

(This line is from experiment E07, the style-reference test: `refs: 1` and the extra 5.37 neurons for the input tile.)

## Storage and retrieval

There is no database. Storage is the file system, with two conventions:

- **Content addressing.** Retrieval is a recomputation: a stage computes the key from the current storyboard and opens `…_<key12>.<ext>`. If the file exists, it is up to date by construction. Old versions stay on disk (for example, rejected keyframes kept as experiment evidence) but are never picked up, because their keys no longer match.
- **What git keeps.** Model outputs (narration, keyframes, references, smoke outputs, the placeholder score, final exports, `runs.jsonl`) are committed. That is what lets a clean clone rebuild without API calls. FFmpeg-derived intermediates are ignored:

@@lines .gitignore:1-20

## How the final outputs are generated

Final outputs are always regenerated by `assemble`:

- The mix is cached by key.
- The two MP4 renders and `report.json` are rebuilt on every run. They are deterministic FFmpeg operations and need no model calls, which keeps the verification honest: the report always describes the files actually on disk.

Table: The current verification report (`outputs/final/report.json`).

| Export | Size | Duration | fps | Integrated loudness | True peak | Checks |
|---|---|---|---|---|---|---|
| vertical | 1080×1920 | 84.42 s | 24 | −14.04 LUFS | −1.76 dBTP | 6 / 6 pass |
| horizontal | 1920×1080 | 84.42 s | 24 | −14.04 LUFS | −1.76 dBTP | 6 / 6 pass |

The report also records `"score_source": "placeholder"`, `"draft"` and `"likeness_shown": false`. `"draft"` was `true` until consent was recorded on 26 November; it has been `false` since. These three flags make the release state explicit.

# Installation and Execution Guide

This chapter is also available as a standalone guide: `docs/technical/SETUP_GUIDE.md`.

## Prerequisites

Table: Required and optional software.

| Software | Version used | Required for | Check |
|---|---|---|---|
| Python | 3.12.3 (3.11+ required) | everything | `python3 --version` |
| python3-venv (Debian/Ubuntu) | — | `make setup` | `python3 -m venv /tmp/t` |
| FFmpeg + ffprobe, with libass | 6.1.1 | shots, music, assembly, radio, tests | `ffmpeg -filters \| grep -w ass` |
| GNU Make | 4.3 | Make targets (or call `run.py` directly) | `make --version` |
| Git | 2.43 | cloning | `git --version` |
| Noto Sans font (recommended) | — | subtitles and end card; DejaVu Sans is the fallback | `fc-list \| grep "Noto Sans"` |
| Gemini API key | free tier | only to regenerate narration | Google AI Studio |
| Cloudflare account ID + Workers AI token | free tier | only to regenerate keyframes | Cloudflare dashboard |
| Kaggle account (phone-verified) | — | only for the Wan 2.2 / ACE-Step stages | kaggle.com |
| LibreOffice | 24.2 | optional, `make report` | `soffice --version` |

Hardware: the local pipeline needs no GPU; it was developed on a CPU-only Linux laptop. A full assembly at 1080p takes about 5.5 minutes there, almost all of it x264 encoding.

## Repository setup

```bash
git clone https://github.com/Yaredo48/heritage-short.git
cd heritage-short
```

The clone includes all model outputs (about 185 MB in `outputs/`).

## Virtual environment and dependencies

```bash
make setup          # python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
```

If `python3 -m venv` fails with "ensurepip is not available", install `python3.12-venv` (needs sudo), or bootstrap pip into the venv with PyPA's `get-pip.py` (`.venv/bin/python -I get-pip.py`), then run `make setup` again.

## Environment configuration and credentials

```bash
cp .env.example .env     # then fill in GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
```

- `.env` is git-ignored; never commit it, and never paste keys into the storyboard or logs.
- Keys are needed **only** to regenerate a narration line or a keyframe. Rebuilding the committed film needs none.
- The Cloudflare token needs only the *Workers AI* permission.
- No database setup is required.

## Execution commands

Table: Commands, with their effect and whether they can call a hosted model.

| Command | Effect | Model calls? |
|---|---|---|
| `make help` | List every target | no |
| `make smoke` | One call per provider, status table | yes (4) |
| `make validate` | Validate the storyboard | no |
| `make timing` | Narration vs shot length, film length | no |
| `make narration` | Stage 4 | only for changed lines |
| `make refs` | Reference-sheet candidates | only for missing candidates |
| `make keyframes` | Stage 1 | only for changed shots |
| `make shots` / `make music` | Stages 2 and 3 | no |
| `make assemble` | Stage 5: both exports and `report.json` | no |
| `make film` | The whole pipeline | only for changed inputs |
| `make shot SHOT=s03` | Regenerate and re-assemble one shot | at most 2 (TTS + image) |
| `make radio` | Radio cut | no |
| `make kaggle-export` / `make import ZIP=…` | Kaggle bridge | no (GPU work happens on Kaggle) |
| `make costs` | Refresh the COSTS.md table | no |
| `make langtest` | E16 language round trip | only for uncached items |
| `make test` | Offline test suite | no |
| `make report` | Report → PDF and DOCX | no |
| `make techdoc` | Rebuild this document (`PROJECT_TECHNICAL_DOCUMENTATION.pdf`) | no |
| `make clean` | Delete derived files only (segments, mixes, tmp) | no |

To force a new take with an unchanged prompt: `.venv/bin/python run.py keyframes --shot s03 --force`.

## Expected behaviour

On a clean clone with no `.env`, `make film` validates, reports every narration line and keyframe as `cached`, re-renders the 18 segments, uses the placeholder score, and assembles and verifies both exports. Abridged console output from the clean-clone run on 25 Nov 2026:

```text
=== validate ===
  warning: likeness consent not recorded: character shots use their no_face_prompt
  warning: script not approved yet: exports will carry a DRAFT mark
storyboard.json v1 is valid: 9 shots, 73s planned including the 3s end card.

=== narration ===
  s01: cached outputs/narration/raw/s01_b76939f591f2.wav
  ...
=== keyframes ===
  s01: cached outputs/keyframes/s01_89745a7392ee.png
  ...
  contact sheet: outputs/keyframes/contact_sheet.jpg
=== shots ===
  s01: ken burns 7.00s -> outputs/shots/vertical/s01_30de81eb3388.mp4, outputs/shots/horizontal/s01_f2f6f8236b4f.mp4
  ...
=== music ===
  using the FFmpeg placeholder pad (temp track)
  score: outputs/music/placeholder_3590b40f2b1d.wav (placeholder)
=== assemble ===
  mix: outputs/final/mix_d63a20fc131a.wav (-14.0 LUFS, score = placeholder)
  vertical: outputs/final/the_silent_language_of_a_mother_s_love_vertical.mp4 1080x1920 84.42s -14.04 LUFS  checks OK
  horizontal: outputs/final/the_silent_language_of_a_mother_s_love_horizontal.mp4 1920x1080 84.42s -14.04 LUFS  checks OK
  note: the score is still the placeholder pad; choose an ACE-Step candidate before release
  note: DRAFT mark is on because consent.script_approved is false
```

## Example: changing one shot

**Input change:** append ", light rain" to `shots[2].image_prompt` (shot s03) in `storyboard.json`.

```bash
make shot SHOT=s03
grep -E '"(model_call|cache_hit)"' runs.jsonl | tail -n 3
```

**Expected result:**

- one new `model_call` line for `keyframes`/`s03` with `status: ok`;
- a `cache_hit` for the unchanged s03 narration;
- two new s03 segments rendered;
- both exports re-assembled and verified.

`make film` would additionally log `cache_hit` for the eight unchanged keyframes and narration lines. This behaviour is asserted by `test_only_the_changed_keyframe_is_regenerated`. Reverting the edit returns to the old keyframe from cache, with no call.

## Common errors and solutions

Table: Error messages the pipeline prints, their causes and fixes.

| Message (as printed) | Cause | Solution |
|---|---|---|
| `Missing GEMINI_API_KEY. Put it in .env (see .env.example).` | A changed input needs a model call and no key is set | Fill in `.env`, or revert the storyboard change |
| `storyboard is invalid:` followed by a list | Schema or cross-field error (typo, unknown field, length outside 60–90 s) | Fix the listed paths; `make validate` |
| `… quota exhausted, provider asks to wait 17.8 h. Cached outputs are kept; rerun later.` | Daily free quota (Gemini TTS: about 10/day) | Rerun after the reset; batch narration edits |
| `<id>: no narration for the current text; run make narration` | A narration line changed but was not regenerated | `make narration` |
| `<id>: keyframe missing (…); run make keyframes` | A prompt changed but no keyframe was generated | `make keyframes` |
| `likeness consent is recorded but references.character.chosen_seed is not set; …` | Consent flag set before choosing a character sheet | `make refs`, then set `references.character.chosen_seed` |
| `consent.likeness_approved is true but ETHICS.md still marks consent as Pending; …` | Flag set without a written consent record | Record consent in ETHICS.md first |
| `music.chosen_seed=N but outputs/music/candidates/seed_N.* is missing; …` | Seed chosen before the Kaggle import | Run the ACE-Step notebook and `make import ZIP=…` |
| `film would be X s; must be 60-90s. …` | Narration or durations changed the length | `make timing`; adjust durations or `voice.max_pause_s` |
| `verification failed; see outputs/final/report.json` | An export failed a check | Read the failing check in `report.json` |
| FFmpeg error `No such filter: 'ass'` | FFmpeg built without libass | Install a full FFmpeg build |
| `make: …/week: No such file or directory` | Old Makefile with an unquoted interpreter path that contains spaces | Use the current Makefile (`"$(PY)"`), or set `PY=` |
| `ensurepip is not available` | Ubuntu without `python3.12-venv` | Install it, or use `get-pip.py` (F01) |

# Testing and Validation

## Testing strategy

The suite follows three rules:

1. **Never call a hosted model.** `fake_providers` replaces `cloudflare_image` and `gemini_tts` with functions that return a generated PNG or a synthetic WAV and record the call. Tests therefore spend no quota and run offline.
2. **Use real FFmpeg.** Filter graphs, subtitle burn-in, loudness measurement and encoding are exercised for real; a broken filter string fails a test.
3. **Isolate state.** The `sandbox` fixture redirects `common.OUTPUTS` and `common.RUNS_LOG` to `tmp_path`, so tests never touch the real outputs or log.

@@code tests/conftest.py::sandbox

@@code tests/conftest.py::fake_providers

## Implemented tests

Table: The 25 tests (`tests/test_storyboard.py`: 10 including 2 parametrised cases; `tests/test_pipeline.py`: 15).

| Test | Verifies | Expected result |
|---|---|---|
| `test_real_storyboard_is_valid` | The committed storyboard has no errors and is 60–90 s | no errors |
| `test_missing_required_field_is_rejected` | Deleting `image_prompt` is caught | error mentions `image_prompt` |
| `test_unknown_field_is_rejected` | A typo field (`camera`) is caught | at least one error |
| `test_length_outside_60_90_is_rejected` | 9 × 12 s shots fail the length rule | "planned length" error |
| `test_duplicate_shot_ids_are_rejected` | Unique ids | "unique" error |
| `test_character_shot_needs_a_no_face_prompt` | Consent fallback is mandatory | `no_face_prompt` error |
| `test_consent_flag_must_match_ethics_record` | Likeness flag vs ETHICS.md, both ways | error only while Pending |
| `test_chosen_seed_must_be_a_candidate` | `music.chosen_seed` must be in `seeds` | `chosen_seed` error |
| `test_render_limits[bad0]`, `[bad1]` | fps 23 and a 5 s transition are rejected | errors |
| `test_retry_then_success` | One 503, then success | log statuses `error, ok`, attempts `1, 2` |
| `test_client_error_is_not_retried` | 400 is final | one log line, no sleep |
| `test_daily_quota_fails_fast` | Real TTS message "retry in 17h50m8s" | `ModelCallError` "quota exhausted", no sleep |
| `test_parse_wait` | "39s" → 39; "17h50m8s" → 64208; no hint → None | exact values |
| `test_only_the_changed_keyframe_is_regenerated` | Edit one prompt among 9 | 10 calls total, the last for that shot; 8 cache hits |
| `test_only_the_changed_narration_is_regenerated` | Edit one Amharic line | 10 TTS calls total |
| `test_pause_setting_changes_no_model_call` | Change `max_pause_s` | 1 TTS call; a new processed file |
| `test_consent_gate_hides_the_face` | Prompt composition with and without consent | `no_face_prompt` without; `image_prompt` + character block with |
| `test_character_sheet_skipped_without_consent` | `make_refs` without consent | no character-sheet prompt sent |
| `test_compress_pauses_shortens_long_silence` | A 1.2 s gap capped at 0.4 s | 0.8 s removed; 2.2 s output (±0.06) |
| `test_subtitle_cues_fit_the_frame` | Every cue, every aspect | 1–2 lines, within width, end > start |
| `test_langtest_scoring` | E16 scoring: punctuation ignored, homophone folding, foreign letters in Ge'ez detected | exact values |
| `test_subtitle_reading_speed` | With the real committed narration, every cue (E15) | ≤ 17 characters/s and ≥ 1 s on screen |
| `test_kaggle_import_places_files_and_merges_log_once` | Import twice | files in place; one Kaggle log line |
| `test_end_to_end_offline` | Whole film at small sizes (180×320, 320×180) | both exports pass verification, 60–90 s, video + audio streams, SRT and ASS written, `mix` logged |

The end-to-end test is the strongest guarantee in the suite:

@@code tests/test_pipeline.py::test_end_to_end_offline

## How to run the tests

```bash
make test                       # = .venv/bin/python -m pytest -q
.venv/bin/python -m pytest -v   # one line per test
.venv/bin/python -m pytest tests/test_pipeline.py -k cache   # a subset
```

## Test results

The suite was executed for this document on **26 November 2026 at 07:37 UTC**, on the author's machine (Python 3.12.3, pytest 9.2.0, FFmpeg 6.1.1):

```text
collected 23 items
tests/test_pipeline.py::test_retry_then_success PASSED
...
tests/test_storyboard.py::test_render_limits[bad1] PASSED
============================= 23 passed in 57.67s ==============================
```

An earlier run, on 25 November, also passed all 23 tests (49 s). After `test_subtitle_reading_speed` was added (E15), the suite was run again on 26 November at about 17:45 EAT: **24 passed in 47.82 s**; after `test_langtest_scoring` was added (E16), **25 passed in 63.84 s**.

## Input validation and runtime verification

Beyond the tests, two checks run on **every real execution**:

- **Validation** (Section 5.2) at the start of every stage.
- **Output verification** (Section 5.7) after every assembly.

Table: The six output checks in `verify()`, and the current results.

| Check | Rule | Current |
|---|---|---|
| `duration_60_90` | 60 ≤ duration ≤ 90 s | 84.42 s ✔ |
| `size` | exactly the storyboard size | 1080×1920 and 1920×1080 ✔ |
| `h264` | video codec is H.264 | ✔ |
| `aac_audio` | an AAC audio stream exists | ✔ |
| `loudness_within_1lu` | integrated loudness within ±1 LU of −14 LUFS | −14.04 ✔ |
| `true_peak_ok` | true peak ≤ −1.5 + 0.5 dBTP | −1.76 ✔ |

## Error-handling verification

The retry tests check the three outcomes of the policy:

- retry then succeed;
- do not retry a client error;
- fail fast on a daily quota.

The behaviour was first observed in production logs before it was tested: 10 failed TTS attempts are recorded in `runs.jsonl` (FAILURES F03, F04).

## Known limitations and untested areas

- **Kaggle notebooks never executed.** Wan 2.2 loading in fp16 with CPU offload, the ACE-Step API names, and the timings are unverified. Only the local import path is tested.
- **Real provider calls are not under automated test.** They are verified by the smoke test and by the real runs recorded in `runs.jsonl` (17 successful keyframe calls, 12 successful narration calls, 1 smoke call each for TTS and Cloudflare).
- **Untested modules:**
  - `script.py`: never executed.
  - `kaggle_io.export()`: executed twice, not unit-tested.
  - `radio.py`: executed, not tested.
  - `costs.py`: executed, not tested.
  - `smoke.py`: executed.
- **Perceptual quality is not tested automatically.** Whether a keyframe hides the face, looks right or matches the culture is checked by eye (F07); the narration's pronunciation needs native-speaker review.
- **Platforms.** Only Linux has been used. The font list includes macOS and Windows paths, but those are untested.

# Design Decisions and Engineering Considerations

This chapter separates **implemented** choices, with the evidence behind them, from ideas that are only possible future work (Chapter 11).

## Why this architecture

Table: Architectural decisions.

| Decision | Reason | Trade-off accepted |
|---|---|---|
| One declarative storyboard as the only contract | A film revision becomes a one-line diff; validation catches errors before quota is spent; the same file drives both aspect ratios | Contract changes need schema updates (deliberately strict: `additionalProperties: false`) |
| Stages communicate through files, not memory | Each stage can run alone; a crash loses nothing; any artefact can be inspected | Some recomputation, such as the timeline, happens in several stages |
| Content-addressed file names as the cache | No cache database to corrupt; freshness is implied by the name; old takes stay on disk as evidence | Keys must list every input. Code changes are not in the keys except where a manual version is included (segments use `"v": 2`) |
| Make + a small Python CLI instead of a workflow engine | The brief asks for "one documented command"; nine stages run sequentially; no extra service to install | No parallelism, no scheduling, no web UI |
| Narration before pictures | Spoken length decides shot length; the 92 s problem appeared before any frame was rendered | A narration edit can shift later shots (their segments re-render; their keyframes do not) |
| Hosted models only through `providers.py` and `call_with_retries` | One place for authentication, retries, logging and cost | A new provider needs a new client function |
| Model outputs committed to git | A clean clone reproduces the film with no keys and no quota | About 185 MB of media in the repository |
| GPU stages bridged by hand-carried zips | No local GPU; manual upload chosen by the author, so no Kaggle credentials are stored | Slow loop; human steps; GPU results arrive asynchronously |

## Why these technologies

Each model choice is justified in Table 2.4. The evidence-backed choices *within* each technology are summarised here:

Table: Alternatives that were actually tried, and the evidence for the choice.

| Question | Alternatives tried | Evidence | Choice |
|---|---|---|---|
| How to shorten the narration | Retake with a faster voice style (E02); FFmpeg `silenceremove` (E03); own pause compressor (E03, E04) | Retake: −12 % on 3 lines, inconsistent, quota exhausted. `silenceremove`: 77.4 → 75.3 s. Own code: 77.4 → 67.9 s at 0.45 s | Own deterministic compressor, `max_pause_s = 0.45` |
| How to keep a consistent look | Style reference image as `input_image_0` (E07) vs a shared text style block | Reference pasted its table and pot into the forest (s02) and lost the dress continuity (s05) | Text style block; `use_style_reference: false` |
| How to name a cultural object | "jebena" (E01) vs shape descriptions (E06) | The name gave a vase; "long narrow neck" gave a pipe; "small round black clay coffee pot with a short spout" worked | Describe by shape |
| How to hide the face | "From behind and slightly to the side" vs "seen from directly behind, her back to the camera" (E05) | The first showed a profile | The second, plus an eye check |
| Subtitle wrapping | Greedy 32-character `textwrap` vs balanced wrapping (E08) | Greedy produced an orphan one-word cue | Balanced, 36 characters vertical |
| Loudness targets | TP −1.0; TP −1.5; TP −1.5 + limiter at −8 and at −10 dBFS (E09) | Only the last reached −14.04 LUFS / −1.76 dBTP after AAC | Pre-limiter −10 dBFS, TP −1.5 |
| Text-model overload | Retries only vs fallback model (F02) | Three 503s of 24–36 s each | Flash → Flash-Lite fallback |

## Performance considerations

Table: Measured local performance (CPU-only laptop).

| Operation | Measured | Dominant cost |
|---|---|---|
| Keyframe (FLUX.2 klein, remote) | mean 9.81 s, 17 calls | network + 4 diffusion steps |
| Narration line (Gemini TTS, remote) | mean 5.74 s, 12 successful calls | remote synthesis |
| 18 Ken Burns segments (9 shots × 2 aspects, 1080p) | 1 min 42 s | `zoompan` at 3× overscale + x264 `veryfast` |
| Assembly, both exports | 5 min 25 s – 5 min 33 s | x264 `medium` at 1080p |
| `make film`, everything cached | 5 min 26 s | assembly |
| `make film`, fresh clone | 7 min 40 s | segments + assembly |
| Test suite | 49–58 s | the end-to-end render at small sizes |

Implemented optimisations:

- caching of every model output, segment and mix;
- `veryfast` x264 for intermediate segments and `medium` only for the final exports;
- 3× overscale only where it removes visible jitter (Ken Burns);
- Kaggle jobs ordered so that shots marked `"wan"` run first within a limited GPU session.

## Maintainability

- **Small modules with one job each.** About 2,100 lines of Python in total, including tests; the largest module, `assemble.py`, is 305 lines.
- **Configuration is data.** Mix, render, voice and consent values live in the storyboard, where they are validated and diffable, not in code.
- **Self-describing outputs.** File names carry keys; `report.json` records the release state; `runs.jsonl` records history.
- **Documentation generated from the code.** This document extracts code by name at build time, and `make costs` regenerates the COSTS.md table from the log.
- **A testability rule.** Path globals are read at call time, so tests can redirect them.

## Scalability limitations

The pipeline is designed for one short film on one machine:

- Model calls are sequential, which is fine at 9 shots and inside free-tier rate limits.
- `runs.jsonl` is read whole by `costs.py` and by Kaggle import deduplication: linear in log size.
- Assembly re-renders the whole film at 1080p whenever it runs, about 5.5 minutes.
- The free tiers, not the code, are the binding limit. With about 10 TTS calls a day, re-narrating 9 lines uses almost a whole day's quota.

## Security considerations

- **Secrets:**
  - Keys are only in `.env`, which is git-ignored from the first commit.
  - `common.env()` reads them; they are sent only in HTTP headers (`x-goog-api-key`, `Authorization: Bearer`).
  - `log_event` is never passed headers or keys: the `params` logged for each call contain sizes, voice, style and prompt *length*, not credentials.
  - Before pushing, the commit range was searched for key patterns (none found).
- **Error text in logs.** Errors are truncated to 300 characters and come from response bodies. A connection error from `requests` can include the request URL, which for Cloudflare contains the account ID (an identifier, not a secret).
- **Private data.**
  - Prompts describe scenes and objects, not names or addresses. The `script` stage's prompt explicitly forbids inventing private details.
  - Free endpoints may use submitted data for training, which is why family details are kept out of prompts (ETHICS.md).
- **Consent as a security property.** The likeness gate cannot be bypassed by editing one flag: the validator also checks the written record.
- **Untrusted downloads.** Kaggle results are imported by path pattern. Only `.mp4` files under `clips/`, `seed_*` files under `music/`, and `runs_kaggle.jsonl` are taken; other members are ignored. File contents are not validated beyond that.

# Limitations and Future Improvements

## Current limitations

Table: Limitations at the time of writing.

| Area | Limitation |
|---|---|
| Moving shots | All 9 shots are Ken Burns over stills; no Wan 2.2 clip has been generated because the notebook has not been run |
| Music | The score is the FFmpeg placeholder pad; no ACE-Step candidate exists yet, so `music.chosen_seed` is null |
| Consent | Recorded 26 Nov for the assignment and its private evaluation only: the film is shared privately, not published, and the no-face version is kept because the repository is public |
| Character consistency | No character reference sheet (consent-gated); the mother is shown only from behind or through her hands |
| Audience | The two required audience tests (radio cut, near-final cut) were not run; DESIGN.md states this, and §6 lists automated checks that are explicitly not audience evidence |
| Language quality | Measured by ASR round trip only (E16: Amharic mean CER 0.123 with homophones folded, four flagged words); not yet reviewed by native listeners. TTS has no seed, so takes are not reproducible |
| Motif accuracy | Keyframes show a generic cup; the real cup's appearance has not been described, and the pipeline does not invent it |
| Script stage | Implemented but never executed |
| Cache keys | Code changes do not invalidate caches automatically, except segments (manual version number); `make clean` or `--force` is needed after changing filter code |
| Platforms | Tested only on Linux |

## Technical challenges encountered

The hardest problems were all **resource limits disguised as bugs**:

- **The TTS daily quota.** A misread "retry in 17h50m8s" wasted retries.
- **The pause-heavy TTS style.** The film ran 2 s over the limit.
- **Overload on the text model.** Three 503s in a row.
- **The image model's misreadings.** It ignored "handleless", did not know "jebena", and drew a profile despite "face hidden".
- **Loudness.** The AAC encoder added 0.2 dB of true peak.

Each was solved by measuring first (log, `silencedetect`, loudnorm), then changing one variable, then recording the result (EXPERIMENTS.md).

## Potential improvements (not implemented)

1. **Run the Kaggle stages.** Generate Wan clips for the shots that need motion (steam, mist), compare them with Ken Burns, and choose an ACE-Step score; log each step as experiments E11–E14.
2. **Code-version-aware cache keys.** Include a hash of the producing function's source in every key, so filter changes invalidate exactly the affected files.
3. **Per-line TTS takes compared by ear.** Several takes per line, rated blind by Amharic speakers; the chosen take is pinned in the storyboard.
4. **Parallel model calls** within rate limits, for example image calls concurrently with TTS.
5. **Faster assembly.** Render only changed segments into a cached concatenation, and encode the final exports once.
6. **Automatic checks of generated images**, for example a face detector that fails a character keyframe if a face is visible while consent is missing.
7. **Unit tests for the untested modules** (`costs`, `radio`, `kaggle_io.export`, `script`).

## Possible extensions

- **More languages.** Afaan Oromo, Tigrinya or Somali narration through the same `voice` block, with a documented record of where TTS fails.
- **A character LoRA** trained on an approved character sheet, with consistency measured across shots.
- **A family-facing tool:** a form that turns a relative's story into a `storyboard.json`, then a film.
- **An MCP server or packaged CLI**, so another agent can render a film from a storyboard.

## Requirements for a more advanced system

Turning this into a multi-user service would need:

- a job queue and worker pool in place of sequential CLI runs;
- an object store with the same content-addressed keys in place of the local `outputs/`;
- a database for runs and approvals in place of `runs.jsonl`;
- authenticated GPU workers in place of manual Kaggle zips;
- a review UI for consent and script approval with an audit trail;
- paid or committed quotas for the models.

The core ideas would carry over unchanged: a validated contract, keys derived from inputs, one logged wrapper per model call, and a consent gate in code.

# Conclusion

## What was developed

A complete, tested, command-line pipeline that turns one validated `storyboard.json` into a finished 60–90 second film. The film has Amharic narration in a stock AI voice, English subtitles, a ducked score, an AI-disclosure end card and loudness-verified exports in 9:16 and 16:9, all built from free-tier generative models and FFmpeg.

## How the pipeline works

1. Validation guards every stage.
2. Narration is generated first and fixes the timeline.
3. Keyframes are generated with consent-aware prompts.
4. Each keyframe becomes a moving segment, as a Wan clip when available or a Ken Burns move otherwise.
5. A score is prepared.
6. Assembly mixes, ducks, normalises, subtitles, renders and verifies both exports.

Every model output is cached under a hash of its inputs; every call is retried sensibly and logged.

## Key implementation achievements

- **Reproducibility:** a fresh clone rebuilt and verified the film with **0 model calls and 18 cache hits**.
- **Incrementality:** editing one shot regenerates only that shot, proven by tests and by the log.
- **Resilience:** quota-aware retries that read the provider's own wait hint and fail fast on daily limits; fallbacks at every GPU-dependent step.
- **Measured quality:** −14.04 LUFS and −1.76 dBTP on both exports; music ducked by 13 dB under speech; six automatic output checks.
- **Ethics in code:** the likeness gate, script-approval watermark and AI disclosure are enforced by the pipeline, not left to memory.
- **Evidence:** more than 170 log lines, 12 recorded experiments, 11 documented failures and 25 passing tests.

## What the project demonstrates technically

Unreliable, rate-limited generative services can be engineered into a dependable production system with modest tools: a strict data contract, content addressing, honest logging and deterministic post-processing. The most valuable fixes were often not more generation but less: a 60-line pause compressor saved a day of TTS quota, and a text style block outperformed a reference image.

# References and Appendix

## Official documentation

Table: References.

| Topic | Reference |
|---|---|
| Gemini API | https://ai.google.dev/gemini-api/docs |
| Gemini speech generation (TTS) | https://ai.google.dev/gemini-api/docs/speech-generation |
| Cloudflare Workers AI | https://developers.cloudflare.com/workers-ai/ |
| Workers AI model catalogue | https://developers.cloudflare.com/workers-ai/models/ |
| Workers AI pricing (neurons) | https://developers.cloudflare.com/workers-ai/platform/pricing/ |
| Wan 2.2 | https://github.com/Wan-Video/Wan2.2 |
| Wan 2.2 TI2V-5B (diffusers weights) | https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers |
| diffusers Wan pipelines | https://huggingface.co/docs/diffusers/api/pipelines/wan |
| ACE-Step 1.5 | https://github.com/ACE-Step/ACE-Step-1.5 |
| Kaggle notebooks | https://www.kaggle.com/docs/notebooks |
| FFmpeg filters | https://ffmpeg.org/ffmpeg-filters.html |
| EBU R 128 loudness | https://tech.ebu.ch/publications/r128 |
| libass (ASS subtitles) | https://github.com/libass/libass |
| JSON Schema 2020-12 | https://json-schema.org/draft/2020-12 |
| jsonschema (Python) | https://python-jsonschema.readthedocs.io/ |
| Requests | https://requests.readthedocs.io/ |
| Pillow | https://pillow.readthedocs.io/ |
| python-dotenv | https://github.com/theskumar/python-dotenv |
| pytest | https://docs.pytest.org/ |
| Mermaid (diagrams in this document) | https://mermaid.js.org/ |

Project documents in the repository: README.md, ARCHITECTURE.md, DESIGN.md, EXPERIMENTS.md, FAILURES.md, COSTS.md, ETHICS.md, SUBMISSION.md.

## Configuration examples

The complete Makefile:

@@lines Makefile:1-64

The `render` and `voice` blocks of the storyboard:

@@json storyboard.json::render

@@json storyboard.json::voice

The Wan parameters sent to Kaggle:

@@code pipeline/kaggle_io.py::WAN_PARAMS

## Useful commands

```bash
# what will the film length be, before rendering?
make timing
# show the model calls and cache hits of the latest run
tail -n 40 runs.jsonl | grep -E '"(model_call|cache_hit)"'
# every failed model attempt, with its error
grep '"status": "error"' runs.jsonl | python3 -c "import sys,json;[print(json.loads(l)['ts'],json.loads(l)['model'],json.loads(l)['error'][:80]) for l in sys.stdin]"
# measure an export independently
ffprobe -v error -show_entries stream=codec_name,width,height:format=duration -of compact outputs/final/*vertical.mp4
ffmpeg -i outputs/final/*vertical.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -12
# rebuild this document (and its diagrams, if mermaid-cli is installed)
docs/technical/render_diagrams.sh && make techdoc
```

## Additional diagram: the cache decision

@@fig cache small | The cache decision used by every generating function (`narration.generate`, `keyframes.generate`, `keyframes.make_refs`); segments, scores and mixes follow the same idea without logging a `cache_hit`.

## Glossary

Table: Glossary.

| Term | Meaning |
|---|---|
| AAC | Advanced Audio Coding; the audio codec of the exports |
| ASS / SRT | Subtitle formats. ASS carries styling and positions (burned in); SRT is plain timed text (uploaded) |
| Atomic write | Writing to a temporary name and renaming, so a reader never sees a half-written file |
| Cache key | SHA-256 of the canonical JSON of every input to an artefact; its first 12 characters are in the file name |
| Consent gate | Code that changes or blocks generation while consent is not recorded |
| Crossfade (`xfade`) | A transition where one shot fades into the next |
| dBTP | Decibels true peak: the inter-sample peak level after reconstruction |
| Ducking | Lowering music automatically while speech is present |
| Exponential backoff | Waiting 2, 4, 8 … seconds between retries (plus jitter) |
| Image-to-video | A diffusion model that animates a still frame (Wan 2.2 TI2V-5B) |
| Keyframe | The still image that defines a shot |
| Ken Burns | A slow zoom or pan across a still image |
| LUFS | Loudness units relative to full scale (EBU R128); −14 LUFS is a common streaming target |
| Linear loudnorm | FFmpeg loudness normalisation that applies one gain, preserving dynamics; needs a first measuring pass |
| Neuron | Cloudflare Workers AI's billing unit; 10,000 per day are free |
| Radio cut | Narration and music on a black screen, used to test the story before pictures exist |
| Seed | The random-number seed that makes an image generation repeatable |
| Sidechain compression | Compression of one signal (music) controlled by another (voice) |
| Stock voice | A provider's predefined synthetic voice, as opposed to a cloned voice |
| T4 | NVIDIA Tesla T4, a 16 GB GPU offered free on Kaggle |
| TTS | Text-to-speech |
| 429 / 503 | HTTP "too many requests" (rate limit or quota) / "service unavailable" (overload) |
