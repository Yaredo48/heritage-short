"""Stage 1, keyframes: one still per shot from FLUX.2 klein 4B on Cloudflare.

  python run.py refs        reference-sheet candidates (style; character only with consent)
  python run.py keyframes   one keyframe per shot [--shot s03] [--force]

Prompt = shot prompt + character block (only with consent) + style block.
Reference images (the chosen style sheet, and the character sheet when consent
is recorded) are sent as input images so every shot is conditioned on them.

Cache key = hash(final prompt, seed, size, model, hashes of reference images).
Edit one shot's prompt and only that keyframe is regenerated; replace the
reference image and every keyframe that used it is regenerated.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from . import common
from .common import canonical_hash, cache_hit, env, file_hash, log_event, rel, write_atomic
from .providers import cloudflare_image
from .validate import load_storyboard

STAGE = "keyframes"


def model_name() -> str:
    return env("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")


def to_png(data: bytes) -> bytes:
    """Cloudflare may return JPEG or PNG; store everything as PNG."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def face_allowed(board: dict) -> bool:
    return board["consent"]["likeness_approved"]


# ---------- reference sheets ----------

def ref_prompt(board: dict, name: str) -> str:
    parts = [board["references"][name]["prompt"]]
    if name == "character":
        parts.append(board["style"]["character_block"])
    parts.append(board["style"]["style_block"])
    return ", ".join(parts)


def ref_key(board: dict, name: str, seed: int) -> str:
    return canonical_hash({"prompt": ref_prompt(board, name), "seed": seed,
                           "size": board["style"]["image_size"], "model": model_name()})


def ref_path(board: dict, name: str, seed: int) -> Path:
    key = ref_key(board, name, seed)
    return common.out_dir("references") / f"{name}_seed{seed}_{key[:12]}.png"


def chosen_ref(board: dict, name: str) -> Path | None:
    seed = board["references"][name].get("chosen_seed")
    if seed is None:
        return None
    path = ref_path(board, name, seed)
    if not path.exists():
        raise SystemExit(f"references.{name}: chosen seed {seed} has no image yet; run `make refs`")
    return path


def make_refs(board: dict, force: bool = False) -> None:
    for name, ref in board["references"].items():
        if name == "character" and not face_allowed(board):
            print("  character sheet skipped: likeness consent is not recorded (consent.likeness_approved=false)")
            log_event("consent_gate", STAGE, item="references.character", action="skipped")
            continue
        w, h = board["style"]["image_size"]
        for seed in ref["seeds"]:
            key = ref_key(board, name, seed)
            path = ref_path(board, name, seed)
            if cache_hit(path, STAGE, f"ref:{name}", key, force):
                print(f"  {name} seed {seed}: cached {rel(path)}")
                continue
            data = cloudflare_image(ref_prompt(board, name), width=w, height=h, seed=seed,
                                    stage=STAGE, shot=f"ref:{name}", cache_key=key, output=rel(path))
            write_atomic(path, to_png(data))
            print(f"  {name} seed {seed}: generated {rel(path)}")
        print(f"  -> look at outputs/references/{name}_*.png and set references.{name}.chosen_seed")


# ---------- keyframes ----------

def shot_prompt(board: dict, shot: dict) -> str:
    show_face = shot["character"] and face_allowed(board)
    text = shot["image_prompt"] if (show_face or not shot["character"]) else shot["no_face_prompt"]
    parts = [text]
    if show_face:
        parts.append(board["style"]["character_block"])
    parts.append(board["style"]["style_block"])
    return ", ".join(parts)


def shot_refs(board: dict, shot: dict) -> list[Path]:
    refs = []
    if board["style"]["use_style_reference"]:
        style = chosen_ref(board, "style")
        if style:
            refs.append(style)
    if shot["character"] and face_allowed(board):
        character = chosen_ref(board, "character")
        if character is None:
            raise SystemExit("likeness consent is recorded but references.character.chosen_seed is not set; "
                             "run `make refs` and choose the golden reference first")
        refs.append(character)
    return refs


def keyframe_key(board: dict, shot: dict) -> str:
    return canonical_hash({
        "prompt": shot_prompt(board, shot), "seed": shot["seed"],
        "size": board["style"]["image_size"], "model": model_name(),
        "refs": [file_hash(r) for r in shot_refs(board, shot)],
    })


def keyframe_path(board: dict, shot: dict) -> Path:
    return common.cache_path(STAGE, shot["id"], keyframe_key(board, shot), "png")


def generate(board: dict, shot: dict, force: bool = False) -> Path:
    key = keyframe_key(board, shot)
    path = common.cache_path(STAGE, shot["id"], key, "png")
    if cache_hit(path, STAGE, shot["id"], key, force):
        print(f"  {shot['id']}: cached {rel(path)}")
        return path
    if shot["character"] and not face_allowed(board):
        log_event("consent_gate", STAGE, shot=shot["id"], action="no_face_prompt used")
    w, h = board["style"]["image_size"]
    refs = shot_refs(board, shot)
    data = cloudflare_image(shot_prompt(board, shot), width=w, height=h, seed=shot["seed"],
                            stage=STAGE, shot=shot["id"], refs=[str(r) for r in refs],
                            cache_key=key, output=rel(path))
    write_atomic(path, to_png(data))
    print(f"  {shot['id']}: generated {rel(path)}")
    return path


def contact_sheet(board: dict, paths: list[Path]) -> Path:
    """One image with every current keyframe, for review (no model call)."""
    thumbs = [Image.open(p).convert("RGB").resize((256, 256)) for p in paths]
    cols = 5
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 256, rows * 256), "black")
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % cols) * 256, (i // cols) * 256))
    out = common.out_dir(STAGE) / "contact_sheet.jpg"
    sheet.save(out, quality=85)
    return out


def main(command, args):
    board = load_storyboard(stage=STAGE)
    if command == "refs":
        make_refs(board, force=args.force)
        return
    shots = [s for s in board["shots"] if not args.shot or s["id"] == args.shot]
    if not shots:
        raise SystemExit(f"no shot {args.shot}")
    for shot in shots:
        generate(board, shot, force=args.force)
    current = [keyframe_path(board, s) for s in board["shots"]]
    if all(p.exists() for p in current):
        print(f"  contact sheet: {rel(contact_sheet(board, current))}")
    log_event("stage_done", STAGE, shots=[s["id"] for s in shots])
