# Walkthrough video plan (at most 5 minutes)

Record the screen with VS Code and a terminal side by side. Pause the recording while long commands run.

| Time | Show | Say (in your own words) |
|---|---|---|
| 0:00–0:30 | The vertical film, first 10 s and the end card | Who it is for (family on Telegram), what they should feel |
| 0:30–1:30 | `ARCHITECTURE.md` diagram, then `storyboard.json` (one shot: reason, prompts, seed, narration, kenburns) and `schema/` | One file is the contract; five stages read it; validation runs before every stage. Show `make validate` failing after deleting a field, then undo |
| 1:30–2:30 | **One hard decision:** `make timing`, then `FAILURES.md` F04/F05 and `pipeline/audio.py` | The narration made the film 92 s; the TTS quota (10/day) ruled out retakes; a deterministic pause cap fixed it with zero model calls |
| 2:30–4:15 | **Live regeneration.** Edit s03's `image_prompt` (e.g. add "light rain"), run `make shot SHOT=s03` (pause during assembly), then `tail -n 30 runs.jsonl \| grep -E 'model_call\|cache_hit'` | One new `model_call` for s03; `cache_hit` for every other keyframe and narration line. Show the new frame in the film |
| 4:15–4:50 | `outputs/final/report.json`, then `COSTS.md` | Both exports verified (duration, size, −14 LUFS); every call is measured |
| 4:50–5:00 | ETHICS.md consent gate | Her face stays hidden until she consents |

Before recording: `make film` once (so everything is cached), and `git stash` any experiments. Afterwards, either keep the s03 change (log it in EXPERIMENTS.md) or revert it and rerun `make film`.
