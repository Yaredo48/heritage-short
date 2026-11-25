"""Script stage: Gemini drafts a storyboard from story/notes.md and DESIGN.md.

It writes storyboard.draft.json and never overwrites storyboard.json:
you read the draft, keep what is good, and copy it over by hand.
Run: python run.py script"""
from __future__ import annotations

import json

from .common import ROOT, log_event
from .providers import gemini_text
from .validate import SCHEMA, check

DRAFT = ROOT / "storyboard.draft.json"

PROMPT = """You are a film director and storyboard writer.
Write a storyboard for a 60-90 second vertical short film, narrated in Amharic
(Ge'ez script) with English subtitle text, from the story notes and design brief below.

Rules:
- Output ONLY JSON that validates against the JSON Schema below.
- 8 to 10 shots; total of shot durations plus render.end_card_s between 60 and 90 seconds.
- One idea and one gentle movement per shot. Vary shot sizes (wide to place, medium for action, close for feeling).
- Every shot has a "reason": its story job and the feeling it carries.
- image_prompt describes what is seen; never ask for text, signs or letters in the image.
- motion_prompt describes only motion and camera (the image already holds the subject).
- Show the mother's face in at most 3 shots ("character": true); elsewhere use hands, back views, places, objects.
- Narration: short spoken Amharic sentences, about 8-14 words per shot. "en" is a faithful English subtitle.
- Use a recurring motif from the notes at the start and the end.
- Do not invent private details (names, addresses) that are not in the notes.

DESIGN BRIEF:
{design}

STORY NOTES:
{notes}

JSON SCHEMA:
{schema}
"""


def main(command, args):
    notes = (ROOT / "story" / "notes.md").read_text(encoding="utf-8")
    design = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    schema = SCHEMA.read_text(encoding="utf-8")
    text = gemini_text(PROMPT.format(design=design, notes=notes, schema=schema),
                       stage="script", json_mode=True, temperature=0.8)
    try:
        board = json.loads(text)
    except json.JSONDecodeError as err:
        DRAFT.with_suffix(".txt").write_text(text, encoding="utf-8")
        raise SystemExit(f"Gemini did not return valid JSON ({err}); raw text saved to storyboard.draft.txt")
    DRAFT.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors, warnings = check(board)
    log_event("script_draft", "script", output=DRAFT.name, valid=not errors, errors=errors[:10])
    print(f"Wrote {DRAFT.name} ({len(board.get('shots', []))} shots).")
    for w in warnings:
        print(f"  warning: {w}")
    if errors:
        print("It does not validate yet; fix these before copying anything over:")
        for e in errors:
            print(f"  - {e}")
