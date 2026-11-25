"""Radio cut: the narration over the score on a black screen, with English
subtitles. The cheapest prototype of the film, for the first audience test
(DESIGN.md). Uses the same timeline and mix as the final film.

Run: python run.py radio   ->  outputs/radio/radio_cut.mp4
"""
from __future__ import annotations

import subprocess

from . import common
from .assemble import CHARS_PER_LINE, cues, mix_audio, write_ass
from .common import log_event, rel
from .narration import film_length, timeline
from .validate import load_storyboard

STAGE = "radio"


def main(command, args):
    board = load_storyboard(stage=STAGE)
    rows = timeline(board)
    total = round(film_length(board, rows), 3)
    audio, stats, source = mix_audio(board, rows, total)
    out_dir = common.out_dir("radio")
    subs = out_dir / "radio_subs.ass"
    write_ass(cues(board, rows, CHARS_PER_LINE["horizontal"]), subs, 1280, 720, "horizontal")
    out = out_dir / "radio_cut.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=24:d={total:.3f}",
                    "-i", str(audio), "-vf", f"ass={subs.name}", "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", out.name],
                   check=True, cwd=out_dir)
    log_event("stage_done", STAGE, output=rel(out), length_s=total, score_source=source)
    print(f"  radio cut: {rel(out)} ({total:.1f}s, score = {source})")
