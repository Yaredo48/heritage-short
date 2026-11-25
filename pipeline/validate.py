"""Validate storyboard.json against schema/storyboard.schema.json, plus checks a
schema cannot express. Every stage calls load_storyboard(), so a broken
storyboard stops the pipeline before any model is called."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .common import ROOT, STORYBOARD, log_event

SCHEMA = ROOT / "schema" / "storyboard.schema.json"
MIN_TOTAL_S, MAX_TOTAL_S = 60, 90
MAX_SUBTITLE_CHARS = 120  # about two cues of two 40-character lines


def check(board: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    def describe(e):
        where = "/".join(map(str, e.path)) or "(root)"
        msg = e.message if len(e.message) < 160 else f"fails '{e.validator}: {e.validator_value}'"
        return f"{where}: {msg}"

    errors = [describe(e) for e in sorted(Draft202012Validator(schema).iter_errors(board),
                                          key=lambda e: list(e.path))]
    warnings: list[str] = []
    if errors:  # cross-field checks assume a structurally valid board
        return errors, warnings

    ids = [s["id"] for s in board["shots"]]
    if len(ids) != len(set(ids)):
        errors.append(f"shot ids must be unique: {ids}")
    total = planned_length(board)
    if not MIN_TOTAL_S <= total <= MAX_TOTAL_S:
        errors.append(f"planned length {total:.1f}s (shots + end card) must be {MIN_TOTAL_S}-{MAX_TOTAL_S}s")
    for s in board["shots"]:
        if s["character"] and "no_face_prompt" not in s:
            errors.append(f"{s['id']}: character shots need a no_face_prompt (used until consent is recorded)")
        if len(s["narration"]["en"]) > MAX_SUBTITLE_CHARS:
            warnings.append(f"{s['id']}: English subtitle is {len(s['narration']['en'])} chars; "
                            f"it will be split into several cues")
    for name, ref in board["references"].items():
        if ref.get("chosen_seed") is not None and ref["chosen_seed"] not in ref["seeds"]:
            errors.append(f"references.{name}.chosen_seed {ref['chosen_seed']} is not one of its seeds")
    chosen = board["music"].get("chosen_seed")
    if chosen is not None and chosen not in board["music"]["seeds"]:
        errors.append(f"music.chosen_seed {chosen} is not one of music.seeds")

    # Consent gate: the flag in the storyboard must agree with the written record.
    if board["consent"]["likeness_approved"] and _ethics_still_pending():
        errors.append("consent.likeness_approved is true but ETHICS.md still marks consent "
                      "as Pending; record how and when consent was given first")
    if not board["consent"]["likeness_approved"] and any(s["character"] for s in board["shots"]):
        warnings.append("likeness consent not recorded: character shots use their no_face_prompt")
    if not board["consent"]["script_approved"]:
        warnings.append("script not approved yet: exports will carry a DRAFT mark")
    return errors, warnings


def planned_length(board: dict) -> float:
    """Shots + end card. Each segment is rendered transition_s longer so the
    crossfades overlap that extra tail and do not shorten the film."""
    return sum(s["duration_s"] for s in board["shots"]) + board["render"]["end_card_s"]


def _ethics_still_pending() -> bool:
    """True if the consent table row for the mother in ETHICS.md says Pending."""
    ethics = ROOT / "ETHICS.md"
    if not ethics.exists():
        return True
    rows = [line for line in ethics.read_text(encoding="utf-8").splitlines()
            if line.startswith("|") and "mother" in line.lower()]
    return not rows or any("pending" in row.lower() for row in rows)


def load_storyboard(path: Path = STORYBOARD, stage: str = "validate") -> dict:
    """Load and validate; raise SystemExit on errors. Used by every stage."""
    board = json.loads(path.read_text(encoding="utf-8"))
    errors, warnings = check(board)
    for w in warnings:
        print(f"  warning: {w}")
    if errors:
        log_event("validation", stage, ok=False, file=path.name, errors=errors[:20])
        raise SystemExit("storyboard is invalid:\n  - " + "\n  - ".join(errors))
    return board


def main(command, args):
    board = load_storyboard()
    total = planned_length(board)
    log_event("validation", "validate", ok=True, file="storyboard.json",
              version=board["version"], shots=len(board["shots"]), total_s=total)
    print(f"storyboard.json v{board['version']} is valid: {len(board['shots'])} shots, "
          f"{total:.0f}s planned including the {board['render']['end_card_s']}s end card.")
