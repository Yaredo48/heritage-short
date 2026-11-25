"""Stage 3, music: prepare the score that assembly mixes under the narration.

ACE-Step 1.5 needs a GPU, so it runs in notebooks/ace_step_music.ipynb on
Kaggle (one candidate per seed in music.seeds). `make import` copies the
candidates to outputs/music/candidates/seed_<n>.wav. This stage then:

  * music.chosen_seed set and its file present -> loudness-match the chosen
    candidate (to -20 LUFS) into outputs/music/score_<key>.wav
  * otherwise -> a quiet A-minor pad synthesised by FFmpeg (a temp track,
    not AI), clearly logged as a placeholder

Run: python run.py music
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import common
from .common import canonical_hash, ffmpeg, file_hash, log_event, rel
from .validate import load_storyboard

STAGE = "music"
PRE_MIX_LUFS = -20  # every source is brought to this before mixing

# A minor - F - C - G, two bars each at the storyboard bpm. Frequencies in Hz.
CHORDS = [(220.00, 261.63, 329.63), (174.61, 220.00, 261.63),
          (130.81, 196.00, 329.63), (196.00, 246.94, 293.66)]


def measure_lufs(path: Path) -> dict:
    """Integrated loudness and true peak via FFmpeg's loudnorm analysis pass."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True)
    data = json.loads(re.search(r"\{[^{}]*\}\s*$", proc.stderr).group(0))
    return {k: float(v) for k, v in data.items() if k.startswith("input_")}


def match_loudness(src: Path, dst: Path, target: float = PRE_MIX_LUFS) -> float:
    """Linear gain so src lands on `target` LUFS; returns the gain in dB."""
    gain = round(target - measure_lufs(src)["input_i"], 2)
    ffmpeg("-i", str(src), "-af", f"volume={gain}dB", "-ar", "48000", "-ac", "2", str(dst))
    return gain


def candidate_path(seed: int) -> Path | None:
    folder = common.OUTPUTS / "music" / "candidates"
    for ext in ("wav", "flac", "mp3"):
        path = folder / f"seed_{seed}.{ext}"
        if path.exists():
            return path
    return None


def placeholder(board: dict) -> Path:
    m = board["music"]
    key = canonical_hash({"kind": "placeholder-pad", "bpm": m["bpm"], "chords": CHORDS,
                          "duration": m["duration_s"]})
    path = common.cache_path(STAGE, "placeholder", key, "wav")
    if path.exists():
        return path
    chord_s = 8 * 60 / m["bpm"]  # two bars of 4/4
    def voice(n):  # pick the n-th note of the current chord
        f = [c[n] for c in CHORDS]
        idx = f"mod(floor(t/{chord_s:.4f}),4)"
        return f"if(eq({idx},0),{f[0]},if(eq({idx},1),{f[1]},if(eq({idx},2),{f[2]},{f[3]})))"
    swell = f"pow(sin(PI*mod(t,{chord_s:.4f})/{chord_s:.4f}),0.6)"  # each chord swells in and out
    expr = "+".join(f"0.08*sin(2*PI*{voice(n)}*t)" for n in range(3))
    ffmpeg("-f", "lavfi", "-i", f"aevalsrc=exprs='({expr})*{swell}':s=48000:d={m['duration_s']}",
           "-af", "lowpass=f=1800,aecho=0.8:0.7:120|240:0.25|0.15,"
                  "afade=t=in:d=2,pan=stereo|c0=c0|c1=c0",
           str(path.with_suffix(".raw.wav")))
    match_loudness(path.with_suffix(".raw.wav"), path)
    path.with_suffix(".raw.wav").unlink()
    log_event("placeholder", STAGE, output=rel(path), note="FFmpeg pad, not a model call")
    return path


def prepare(board: dict) -> tuple[Path, str]:
    """Return (score file, source) where source is 'ace-step seed N' or 'placeholder'."""
    m = board["music"]
    seed = m.get("chosen_seed")
    if seed is not None:
        src = candidate_path(seed)
        if src is None:
            raise SystemExit(f"music.chosen_seed={seed} but outputs/music/candidates/seed_{seed}.* "
                             f"is missing; run the Kaggle notebook and `make import`")
        key = canonical_hash({"src": file_hash(src), "target": PRE_MIX_LUFS})
        path = common.cache_path(STAGE, f"score_seed{seed}", key, "wav")
        if not path.exists():
            gain = match_loudness(src, path)
            log_event("prepare", STAGE, source=rel(src), output=rel(path), gain_db=gain)
        return path, f"ace-step seed {seed}"
    found = [s for s in m["seeds"] if candidate_path(s)]
    if found:
        print(f"  ACE-Step candidates present for seeds {found}; listen, then set music.chosen_seed")
    print("  using the FFmpeg placeholder pad (temp track)")
    return placeholder(board), "placeholder"


def main(command, args):
    board = load_storyboard(stage=STAGE)
    path, source = prepare(board)
    print(f"  score: {rel(path)} ({source})")
    log_event("stage_done", STAGE, output=rel(path), source=source)
