"""Stage 4, narration: one Amharic WAV per shot from Gemini TTS (stock voice).

Two files per shot:
  outputs/narration/raw/<id>_<key>.wav   what the model returned (the only paid/quota step)
  outputs/narration/<id>_<key>_p<ms>.wav raw with long pauses shortened (FFmpeg-free, deterministic)
Cache key = hash(Amharic text, voice, style, model). Change one narration line
and only that shot calls the model again. Changing max_pause_s calls nothing.

Also owns timeline(): the narration sets the pace of the film, so a shot is
stretched when its spoken line is longer than the planned duration.

Run: python run.py narration [--shot s03] [--force]
     python run.py timing      # narration length against shot length
"""
from __future__ import annotations

from pathlib import Path

from . import common
from .common import canonical_hash, cache_hit, duration_s, env, log_event, rel, write_atomic
from .audio import compress_pauses
from .providers import gemini_tts
from .validate import load_storyboard

STAGE = "narration"
MIN_GAP_S = 0.6  # silence after a line before the next shot's line can start


def narration_key(board: dict, shot: dict) -> str:
    return canonical_hash({
        "text": shot["narration"]["am"],
        "voice": board["voice"]["voice"],
        "style": board["voice"]["style"],
        "model": env("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts"),
    })


def raw_path(board: dict, shot: dict) -> Path:
    return common.cache_path(f"{STAGE}/raw", shot["id"], narration_key(board, shot), "wav")


def narration_path(board: dict, shot: dict) -> Path:
    """The processed file every later stage uses."""
    key = narration_key(board, shot)
    pause_ms = int(round(board["voice"]["max_pause_s"] * 1000))
    return common.out_dir(STAGE) / f"{shot['id']}_{key[:12]}_p{pause_ms}.wav"


def generate(board: dict, shot: dict, force: bool = False) -> Path:
    key = narration_key(board, shot)
    raw = raw_path(board, shot)
    if cache_hit(raw, STAGE, shot["id"], key, force):
        print(f"  {shot['id']}: cached {rel(raw)}")
    else:
        audio = gemini_tts(shot["narration"]["am"], style=board["voice"]["style"],
                           voice=board["voice"]["voice"], stage=STAGE, shot=shot["id"],
                           cache_key=key, output=rel(raw))
        write_atomic(raw, audio)
        print(f"  {shot['id']}: generated {rel(raw)} ({duration_s(raw):.2f}s)")
    path = narration_path(board, shot)
    if force or not path.exists():
        info = compress_pauses(raw, path, board["voice"]["max_pause_s"])
        print(f"  {shot['id']}: pauses capped -> {rel(path)} ({info['in_s']:.2f}s -> {info['out_s']:.2f}s)")
    return path


def timeline(board: dict, require_audio: bool = True) -> list[dict]:
    """Start time and effective duration of every shot.

    A shot lasts max(planned duration, lead-in + narration + MIN_GAP_S), so a long
    line never runs into the next shot. Missing narration counts as 0 s unless
    require_audio is set.
    """
    lead_in = board["render"]["lead_in_s"]
    t, rows = 0.0, []
    for shot in board["shots"]:
        path = narration_path(board, shot)
        if path.exists():
            narr = duration_s(path)
        elif require_audio:
            raise SystemExit(f"{shot['id']}: no narration for the current text; run `make narration`")
        else:
            path, narr = None, 0.0
        dur = round(max(shot["duration_s"], lead_in + narr + MIN_GAP_S), 3)
        rows.append({"id": shot["id"], "start": round(t, 3), "dur": dur,
                     "narration": path, "narr_s": round(narr, 3), "shot": shot})
        t += dur
    return rows


def film_length(board: dict, rows: list[dict]) -> float:
    return sum(r["dur"] for r in rows) + board["render"]["end_card_s"]


def main(command, args):
    board = load_storyboard(stage=STAGE)
    if command == "timing":
        rows = timeline(board, require_audio=False)
        print(f"{'shot':<6}{'planned':>8}{'narration':>11}{'used':>7}  note")
        for r in rows:
            note = "stretched to fit the line" if r["dur"] > r["shot"]["duration_s"] else ""
            if r["narration"] is None:
                note = "no narration yet"
            print(f"{r['id']:<6}{r['shot']['duration_s']:>8}{r['narr_s']:>11.2f}{r['dur']:>7.2f}  {note}")
        print(f"film length with end card: {film_length(board, rows):.1f}s (must be 60-90)")
        return
    shots = [s for s in board["shots"] if not args.shot or s["id"] == args.shot]
    if not shots:
        raise SystemExit(f"no shot {args.shot}")
    for shot in shots:
        generate(board, shot, force=args.force)
    log_event("stage_done", STAGE, shots=[s["id"] for s in shots])
