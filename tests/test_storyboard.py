"""The storyboard contract: schema plus the checks a schema cannot express."""
import pytest

from pipeline import validate
from pipeline.validate import check, planned_length


def errors_of(board):
    return check(board)[0]


def test_real_storyboard_is_valid(board):
    assert errors_of(board) == []
    assert 60 <= planned_length(board) <= 90


def test_missing_required_field_is_rejected(board):
    del board["shots"][0]["image_prompt"]
    assert any("image_prompt" in e for e in errors_of(board))


def test_unknown_field_is_rejected(board):
    board["shots"][0]["camera"] = "dolly"  # typos must not pass silently
    assert errors_of(board)


def test_length_outside_60_90_is_rejected(board):
    for s in board["shots"]:
        s["duration_s"] = 12
    assert any("planned length" in e for e in errors_of(board))


def test_duplicate_shot_ids_are_rejected(board):
    board["shots"][1]["id"] = board["shots"][0]["id"]
    assert any("unique" in e for e in errors_of(board))


def test_character_shot_needs_a_no_face_prompt(board):
    shot = next(s for s in board["shots"] if s["character"])
    del shot["no_face_prompt"]
    assert any("no_face_prompt" in e for e in errors_of(board))


def test_consent_flag_must_match_ethics_record(board, monkeypatch):
    board["consent"]["likeness_approved"] = True
    monkeypatch.setattr(validate, "_ethics_still_pending", lambda: True)
    assert any("ETHICS.md" in e for e in errors_of(board))
    monkeypatch.setattr(validate, "_ethics_still_pending", lambda: False)
    assert not any("ETHICS.md" in e for e in errors_of(board))


def test_chosen_seed_must_be_a_candidate(board):
    board["music"]["chosen_seed"] = 999
    assert any("chosen_seed" in e for e in errors_of(board))


@pytest.mark.parametrize("bad", [{"fps": 23}, {"transition_s": 5}])
def test_render_limits(board, bad):
    board["render"].update(bad)
    assert errors_of(board)
