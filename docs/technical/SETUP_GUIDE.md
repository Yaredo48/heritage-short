# Setup and execution guide

How to install the Heritage Short pipeline from a clean machine, rebuild the film, change one shot and troubleshoot. Chapter 8 of `PROJECT_TECHNICAL_DOCUMENTATION.pdf` covers the same ground in more detail.

## 1. Prerequisites

| Software | Version used | Needed for |
|---|---|---|
| Python | 3.12.3 (3.11 or newer) | everything |
| `python3-venv` (Debian/Ubuntu) | — | `make setup` |
| FFmpeg + ffprobe **with libass** | 6.1.1 | shots, music, assembly, tests (`ffmpeg -filters \| grep -w ass`) |
| GNU Make | 4.3 | the `make` targets (or call `python run.py <command>` directly) |
| Git | any recent | cloning |
| Noto Sans font | — | subtitles and end card (DejaVu Sans is the fallback) |

Only needed to **regenerate** model outputs:
- a Gemini API key, from Google AI Studio (free tier), for narration;
- a Cloudflare account ID and a token with the *Workers AI* permission, for keyframes;
- a phone-verified Kaggle account, for the Wan 2.2 and ACE-Step notebooks.

No GPU is needed locally, and there is no database.

## 2. Install

```bash
git clone https://github.com/Yaredo48/heritage-short.git
cd heritage-short
make setup                 # creates .venv and installs requirements.txt
```

If `make setup` fails with `ensurepip is not available`, either install `python3.12-venv` (needs sudo), or bootstrap pip into the venv and repeat the install:

```bash
curl -sSLO https://bootstrap.pypa.io/get-pip.py
.venv/bin/python -I get-pip.py
.venv/bin/python -m pip install -r requirements.txt
```

## 3. Configure (optional)

```bash
cp .env.example .env       # fill in GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
make smoke                 # one call per provider; prints a status table
```

`.env` is git-ignored. Never commit it, and never put keys in `storyboard.json`.

## 4. Rebuild the film

```bash
make test                  # 23 offline tests, about 1 minute; no API calls
make film                  # validate → narration → keyframes → shots → music → assemble
```

On a clean clone every narration line and keyframe is reported as `cached` (all model outputs are committed). FFmpeg re-renders the segments and assembles both exports in about 7–8 minutes on a CPU laptop.

**Outputs** (in `outputs/final/`):
- `the_silent_language_of_a_mother_s_love_vertical.mp4` (1080×1920)
- `the_silent_language_of_a_mother_s_love_horizontal.mp4` (1920×1080)
- `subtitles_en.srt`
- `report.json`: duration, size, codecs, loudness and true peak, each with a pass/fail check

## 5. Change one shot and regenerate only that shot

1. Edit one shot in `storyboard.json`: its `image_prompt` (or `no_face_prompt` while consent is pending), its `seed`, its `kenburns` direction, or its `narration.am` line.
2. Run `make shot SHOT=s03`, or `make film`; the cache gives the same result.
3. Check the log:
   ```bash
   tail -n 40 runs.jsonl | grep -E '"(model_call|cache_hit)"'
   ```
   It shows one new `model_call` for the changed shot, and `cache_hit` for everything else.

To force a new take of an unchanged prompt: `.venv/bin/python run.py keyframes --shot s03 --force`.

## 6. Other useful commands

| Command | What it does |
|---|---|
| `make timing` | Shows narration length against shot length, and the film length, before rendering |
| `make radio` | Radio cut (narration and score on black, subtitled) for audience tests |
| `make kaggle-export` / `make import ZIP=…` | Packs GPU jobs for Kaggle and brings the results back |
| `make costs` | Rebuilds the COSTS.md table from `runs.jsonl` |
| `make report` | Converts `docs/REPORT.md` to PDF and DOCX (needs LibreOffice) |
| `make techdoc` | Rebuilds `PROJECT_TECHNICAL_DOCUMENTATION.pdf` (needs Google Chrome and poppler-utils) |
| `make clean` | Deletes derived files only (segments, mixes, tmp); model outputs are kept |

## 7. GPU stages on Kaggle (not yet run)

1. Run `make kaggle-export`. It writes `kaggle/heritage_job.zip` (the keyframes plus `jobs.json`).
2. On Kaggle, upload the zip as a dataset. In each of `notebooks/wan_video.ipynb` and `notebooks/ace_step_music.ipynb`: add the dataset, choose *GPU T4*, turn *Internet* on, and *Run all*.
3. Download `heritage_results.zip` and run `make import ZIP=~/Downloads/heritage_results.zip`.
4. Set `"video": "wan"` on the shots whose clips you want to use. Set `music.chosen_seed` and `music.choice_reason`. Then run `make film`.

## 8. Troubleshooting

| Message | Fix |
|---|---|
| `Missing GEMINI_API_KEY. Put it in .env (see .env.example).` | Add the key, or revert the storyboard change that needs a new call |
| `storyboard is invalid:` followed by a list | Fix the listed fields, then run `make validate` |
| `… quota exhausted, provider asks to wait N h. Cached outputs are kept; rerun later.` | The daily free quota is used up (Gemini TTS allows about 10 calls a day); rerun after the reset |
| `no narration for the current text; run make narration` | Run `make narration` |
| `keyframe missing (…); run make keyframes` | Run `make keyframes` |
| `consent.likeness_approved is true but ETHICS.md still marks consent as Pending` | Record the consent in ETHICS.md first |
| `likeness consent is recorded but references.character.chosen_seed is not set` | Run `make refs`, then choose a seed |
| `film would be X s; must be 60-90s` | Run `make timing`, then adjust shot durations or `voice.max_pause_s` |
| `verification failed; see outputs/final/report.json` | Read the failing check in `report.json` |
| FFmpeg: `No such filter: 'ass'` | Install an FFmpeg build that includes libass |
