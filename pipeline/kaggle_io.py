"""Bridge to the Kaggle GPU notebooks (Wan 2.2 clips, ACE-Step music).

  python run.py kaggle-export   -> kaggle/heritage_job.zip
      jobs.json + the current keyframes. Upload it to Kaggle as a dataset and
      attach it to notebooks/wan_video.ipynb and notebooks/ace_step_music.ipynb.
  python run.py kaggle-import --zip <downloaded results.zip>
      clips   -> outputs/shots/wan/<shot>_<keyframe key>.mp4
      music   -> outputs/music/candidates/seed_<n>.<ext>
      the notebooks' runs_kaggle.jsonl lines are appended to runs.jsonl, so
      GPU calls are logged exactly like local calls.

A clip's file name carries the hash of the keyframe it was made from, so a
clip made from an old keyframe is never used for a new one.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from . import common
from .common import ROOT, log_event, now_iso, rel
from .keyframes import keyframe_key, keyframe_path
from .validate import load_storyboard

STAGE = "kaggle"
KAGGLE = ROOT / "kaggle"
WAN_PARAMS = {"model": "Wan-AI/Wan2.2-TI2V-5B-Diffusers", "max_area": 480 * 832, "num_frames": 121,
              "fps": 24, "steps": 30, "guidance_scale": 5.0,
              "negative_prompt": "fast motion, camera shake, morphing, warping, distorted hands, extra fingers, "
                                 "text, watermark, flicker, blurry"}
HIDE_FACE = " She keeps her back to the camera and her face stays hidden."


def export(board: dict) -> Path:
    job_dir = KAGGLE / "job"
    if job_dir.exists():
        shutil.rmtree(job_dir)
    (job_dir / "keyframes").mkdir(parents=True)
    wan = []
    # Shots marked "wan" first, then the rest, so a short GPU session does the important ones.
    ordered = sorted(board["shots"], key=lambda s: s["video"] != "wan")
    for shot in ordered:
        kf = keyframe_path(board, shot)
        if not kf.exists():
            raise SystemExit(f"{shot['id']}: keyframe missing; run `make keyframes` first")
        shutil.copy(kf, job_dir / "keyframes" / kf.name)
        prompt = shot["motion_prompt"]
        if shot["character"] and not board["consent"]["likeness_approved"]:
            prompt += HIDE_FACE  # consent gate also applies to motion
        wan.append({"shot": shot["id"], "keyframe": f"keyframes/{kf.name}", "prompt": prompt,
                    "seed": shot["seed"], "out": f"{shot['id']}_{keyframe_key(board, shot)[:12]}.mp4",
                    "marked_wan": shot["video"] == "wan"})
    m = board["music"]
    jobs = {"created": now_iso(), "storyboard_version": board["version"], "wan_params": WAN_PARAMS,
            "wan": wan, "music": {"model": "ACE-Step 1.5 (acestep-v15-turbo)", "caption": m["caption"],
                                  "bpm": m["bpm"], "keyscale": m["keyscale"],
                                  "duration": m["duration_s"], "seeds": m["seeds"]}}
    (job_dir / "jobs.json").write_text(json.dumps(jobs, indent=2, ensure_ascii=False))
    out = KAGGLE / "heritage_job.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(job_dir.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(job_dir))
    log_event("export", STAGE, output=rel(out), wan_jobs=len(wan), music_seeds=m["seeds"])
    return out


def import_results(zip_path: Path) -> dict:
    counts = {"clips": 0, "music": 0, "log_lines": 0}
    known = set()
    if common.RUNS_LOG.exists():
        known = {line.strip() for line in common.RUNS_LOG.read_text(encoding="utf-8").splitlines()}
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            base = Path(name).name
            if name.endswith("/") or not base:
                continue
            if "clips/" in name and base.endswith(".mp4"):
                dst = common.out_dir("shots", "wan") / base
                counts["clips"] += 1
            elif "music/" in name and base.startswith("seed_"):
                dst = common.out_dir("music", "candidates") / base
                counts["music"] += 1
            elif base == "runs_kaggle.jsonl":
                with common.RUNS_LOG.open("a", encoding="utf-8") as log:
                    for line in z.read(name).decode("utf-8").splitlines():
                        if line.strip() and line.strip() not in known:
                            log.write(line.strip() + "\n")
                            counts["log_lines"] += 1
                continue
            else:
                continue
            dst.write_bytes(z.read(name))
    log_event("import", STAGE, source=str(zip_path), **counts)
    return counts


def main(command, args):
    board = load_storyboard(stage=STAGE)
    if command == "kaggle-export":
        out = export(board)
        print(f"  wrote {rel(out)}: upload it to Kaggle as a dataset (see README, 'GPU stages')")
    else:
        if not args.zip:
            raise SystemExit("usage: python run.py kaggle-import --zip path/to/heritage_results.zip")
        counts = import_results(Path(args.zip))
        print(f"  imported {counts['clips']} clips, {counts['music']} music candidates, "
              f"{counts['log_lines']} log lines")
