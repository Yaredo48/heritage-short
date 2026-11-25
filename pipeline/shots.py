"""Stage 2, moving shots: one video segment per shot and aspect ratio.

Source for each shot:
  * video == "wan" and a Wan 2.2 clip exists for the CURRENT keyframe
    (outputs/shots/wan/<id>_<keyframe key>.mp4, brought back by `make import`)
    -> the clip, centre-cropped and gently slowed to fill the shot
  * otherwise -> Ken Burns: a slow zoom or pan over the keyframe (FFmpeg)

So the film can always be finished, even with no GPU at all. A Wan clip is
tied to the keyframe it was made from: change the keyframe and the old clip is
ignored until a new one is imported.

Each segment is rendered transition_s longer than the shot so the crossfade in
assembly overlaps that tail. Segments are cached by hash of their inputs.

Run: python run.py shots [--shot s03] [--force]
"""
from __future__ import annotations

from pathlib import Path

from . import common
from .common import canonical_hash, duration_s, ffmpeg, file_hash, log_event, rel
from .keyframes import keyframe_key, keyframe_path
from .narration import timeline
from .validate import load_storyboard

STAGE = "shots"
ZOOM = 1.12  # how far Ken Burns moves: 12 % zoom, or a pan across that margin
OVERSCALE = 3  # zoompan rounds to whole pixels; working 3x larger hides the jitter


def wan_clip(board: dict, shot: dict) -> Path | None:
    path = common.OUTPUTS / "shots" / "wan" / f"{shot['id']}_{keyframe_key(board, shot)[:12]}.mp4"
    return path if path.exists() else None


def kenburns_filter(direction: str, w: int, h: int, frames: int, fps: int) -> str:
    """Crop the square keyframe to the output aspect, then zoom or pan slowly."""
    p = f"(on/{max(frames - 1, 1)})"  # progress 0 -> 1
    ease = f"(0.5-0.5*cos(PI*{p}))"  # ease in and out
    z = {"in": f"1+{ZOOM - 1}*{ease}", "out": f"{ZOOM}-{ZOOM - 1}*{ease}"}.get(direction, str(ZOOM))
    cx, cy = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    x = {"left": f"(iw-iw/zoom)*(1-{ease})", "right": f"(iw-iw/zoom)*{ease}"}.get(direction, cx)
    y = {"up": f"(ih-ih/zoom)*(1-{ease})", "down": f"(ih-ih/zoom)*{ease}"}.get(direction, cy)
    return (f"crop='min(iw,ih*{w}/{h})':'min(ih,iw*{h}/{w})',"
            f"scale={w * OVERSCALE}:{h * OVERSCALE}:flags=lanczos,"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps},"
            f"setsar=1,format=yuv420p")


def clip_filter(clip_s: float, length: float, w: int, h: int, fps: int) -> str:
    """Cover-crop a Wan clip to the aspect; slow it by up to 1.6x, then hold the last frame."""
    stretch = min(max(length / clip_s, 1.0), 1.6)
    hold = max(length - clip_s * stretch, 0) + 0.1
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"setpts={stretch:.4f}*PTS,fps={fps},tpad=stop_mode=clone:stop_duration={hold:.3f},"
            f"trim=duration={length:.3f},setsar=1,format=yuv420p")


def segment(board: dict, row: dict, aspect: str, force: bool = False) -> Path:
    shot = row["shot"]
    w, h = board["render"]["sizes"][aspect]
    fps = board["render"]["fps"]
    length = round(row["dur"] + board["render"]["transition_s"], 3)
    clip = wan_clip(board, shot) if shot["video"] == "wan" else None
    source = clip or keyframe_path(board, shot)
    if not source.exists():
        raise SystemExit(f"{shot['id']}: keyframe missing ({rel(source)}); run `make keyframes`")
    method = "wan" if clip else "kenburns"
    key = canonical_hash({"source": file_hash(source), "method": method, "dir": shot["kenburns"],
                          "length": length, "size": [w, h], "fps": fps, "zoom": ZOOM, "v": 2})
    path = common.cache_path(f"{STAGE}/{aspect}", shot["id"], key, "mp4")
    if path.exists() and not force:
        return path
    if clip:
        vf = clip_filter(duration_s(clip), length, w, h, fps)
        ffmpeg("-i", str(clip), "-vf", vf, "-an", "-c:v", "libx264", "-crf", "18",
               "-preset", "veryfast", "-r", str(fps), str(path))
    else:
        frames = int(round(length * fps))
        vf = kenburns_filter(shot["kenburns"], w, h, frames, fps)
        ffmpeg("-loop", "1", "-i", str(source), "-vf", vf, "-frames:v", str(frames),
               "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-r", str(fps), str(path))
    log_event("render", STAGE, shot=shot["id"], aspect=aspect, method=method,
              source=rel(source), output=rel(path), length_s=length)
    return path


def main(command, args):
    board = load_storyboard(stage=STAGE)
    rows = [r for r in timeline(board) if not args.shot or r["id"] == args.shot]
    if not rows:
        raise SystemExit(f"no shot {args.shot}")
    for row in rows:
        made = []
        for aspect in board["render"]["sizes"]:
            path = segment(board, row, aspect, force=args.force)
            made.append(rel(path))
        clip = wan_clip(board, row["shot"]) if row["shot"]["video"] == "wan" else None
        print(f"  {row['id']}: {'wan clip' if clip else 'ken burns'} {row['dur']:.2f}s -> {', '.join(made)}")
    log_event("stage_done", STAGE, shots=[r["id"] for r in rows])
