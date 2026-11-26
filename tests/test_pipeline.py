"""Stages, cache, retries, consent gate and a full offline render."""
import json
import subprocess
import zipfile
from pathlib import Path

import pytest
import requests

from pipeline import assemble, common, keyframes, narration
from pipeline.audio import compress_pauses
from pipeline.common import ModelCallError, call_with_retries, parse_wait

from .conftest import fake_wav, log_lines


# ---------- retries ----------

class FakeResp:
    def __init__(self, status, text=""):
        self.status_code, self.text, self.headers = status, text, {}


def http_error(status, text=""):
    return requests.HTTPError(f"HTTP {status}: {text}", response=FakeResp(status, text))


def test_retry_then_success(sandbox, monkeypatch):
    monkeypatch.setattr(common.time, "sleep", lambda s: None)
    outcomes = [http_error(503), ("result", {})]

    def fn():
        item = outcomes.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    assert call_with_retries(fn, stage="t", shot="s01", provider="p", model="m", params={}) == "result"
    lines = log_lines(sandbox)
    assert [l["status"] for l in lines] == ["error", "ok"]
    assert [l["attempt"] for l in lines] == [1, 2]


def test_client_error_is_not_retried(sandbox, monkeypatch):
    monkeypatch.setattr(common.time, "sleep", lambda s: pytest.fail("should not wait"))

    def fn():
        raise http_error(400, "bad request")

    with pytest.raises(ModelCallError):
        call_with_retries(fn, stage="t", shot=None, provider="p", model="m", params={})
    assert len(log_lines(sandbox)) == 1


def test_daily_quota_fails_fast(sandbox, monkeypatch):
    """The real Gemini TTS message: waiting 17 h inside a run is pointless."""
    monkeypatch.setattr(common.time, "sleep", lambda s: pytest.fail("should not wait"))

    def fn():
        raise http_error(429, "limit: 10 requests per day. Please retry in 17h50m8s")

    with pytest.raises(ModelCallError, match="quota exhausted"):
        call_with_retries(fn, stage="t", shot=None, provider="p", model="m", params={})


def test_parse_wait():
    assert parse_wait("Please retry in 39s") == 39
    assert parse_wait("retry in 17h50m8s") == 17 * 3600 + 50 * 60 + 8
    assert parse_wait("no hint") is None


# ---------- cache ----------

def test_only_the_changed_keyframe_is_regenerated(sandbox, board, fake_providers):
    for s in board["shots"]:
        keyframes.generate(board, s)
    assert len(fake_providers["image"]) == len(board["shots"])

    board["shots"][2]["image_prompt"] += ", light rain"
    for s in board["shots"]:
        keyframes.generate(board, s)
    assert len(fake_providers["image"]) == len(board["shots"]) + 1
    assert fake_providers["image"][-1]["shot"] == board["shots"][2]["id"]
    hits = [l for l in log_lines(sandbox) if l["event"] == "cache_hit"]
    assert len(hits) == len(board["shots"]) - 1


def test_only_the_changed_narration_is_regenerated(sandbox, board, fake_providers):
    for s in board["shots"]:
        narration.generate(board, s)
    board["shots"][0]["narration"]["am"] += " ።"
    for s in board["shots"]:
        narration.generate(board, s)
    assert len(fake_providers["tts"]) == len(board["shots"]) + 1


def test_pause_setting_changes_no_model_call(sandbox, board, fake_providers):
    shot = board["shots"][0]
    first = narration.generate(board, shot)
    board["voice"]["max_pause_s"] = 0.3
    second = narration.generate(board, shot)
    assert len(fake_providers["tts"]) == 1
    assert first != second and second.exists()


# ---------- consent gate ----------

def test_consent_gate_hides_the_face(board):
    shot = next(s for s in board["shots"] if s["character"])
    board["consent"]["likeness_approved"] = False
    prompt = keyframes.shot_prompt(board, shot)
    assert prompt.startswith(shot["no_face_prompt"])
    assert board["style"]["character_block"] not in prompt

    board["consent"]["likeness_approved"] = True
    prompt = keyframes.shot_prompt(board, shot)
    assert prompt.startswith(shot["image_prompt"])
    assert board["style"]["character_block"] in prompt


def test_character_sheet_skipped_without_consent(sandbox, board, fake_providers):
    board["consent"]["likeness_approved"] = False
    keyframes.make_refs(board)
    assert all("character reference sheet" not in c["prompt"] for c in fake_providers["image"])


# ---------- audio helpers and subtitles ----------

def test_compress_pauses_shortens_long_silence(tmp_path):
    src, dst = tmp_path / "in.wav", tmp_path / "out.wav"
    src.write_bytes(fake_wav(seconds=3.0, pause_at=1.0, pause_s=1.2))
    info = compress_pauses(src, dst, max_pause_s=0.4)
    assert info["removed_s"] == pytest.approx(0.8, abs=0.06)
    assert common.duration_s(dst) == pytest.approx(2.2, abs=0.06)


def test_subtitle_cues_fit_the_frame(board, sandbox, fake_providers):
    for s in board["shots"]:
        narration.generate(board, s)
    rows = narration.timeline(board)
    for aspect, width in assemble.CHARS_PER_LINE.items():
        for start, end, lines in assemble.cues(board, rows, width):
            assert 1 <= len(lines) <= 2
            assert all(len(line) <= width for line in lines)
            assert end > start


def test_subtitle_reading_speed(board):
    """EXPERIMENTS.md E15: with the real (committed) narration, every cue is readable
    on a phone: at most 17 characters per second and at least 1 s on screen."""
    if not all(narration.narration_path(board, s).exists() for s in board["shots"]):
        pytest.skip("real narration not generated for the current storyboard")
    rows = narration.timeline(board)
    for width in assemble.CHARS_PER_LINE.values():
        for start, end, lines in assemble.cues(board, rows, width):
            assert end - start >= 1.0
            assert len(" ".join(lines)) / (end - start) <= 17


def test_langtest_scoring():
    """E16 scoring: punctuation and spaces ignored; Amharic homophone letters folded on request;
    foreign letters inside Ge'ez text are detected."""
    from pipeline.langtest import cer, fold_homophones, non_script_letters
    assert cer("Hello, World!", "hello world") == 0
    assert cer("ሕልሞች።", "ህልሞች") > 0 and cer("ሕልሞች።", "ህልሞች", fold=True) == 0
    assert fold_homophones("ሠዋች ዕድል") == "ሰዋች እድል"
    assert non_script_letters("куሉ ፡ ታሪኽ") == "ку"
    assert cer("abcd", "abxd") == 0.25


# ---------- Kaggle bridge ----------

def test_kaggle_import_places_files_and_merges_log_once(sandbox):
    from pipeline.kaggle_io import import_results
    z = sandbox / "results.zip"
    line = json.dumps({"event": "model_call", "stage": "shots", "provider": "kaggle", "status": "ok"})
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("results/clips/s01_abc.mp4", b"x")
        f.writestr("results/music/seed_11.wav", b"y")
        f.writestr("results/runs_kaggle.jsonl", line + "\n")
    import_results(z)
    import_results(z)  # importing twice must not duplicate the log
    assert (common.OUTPUTS / "shots/wan/s01_abc.mp4").exists()
    assert (common.OUTPUTS / "music/candidates/seed_11.wav").exists()
    assert sum(1 for l in log_lines(sandbox) if l.get("provider") == "kaggle") == 1


# ---------- the whole film, offline ----------

def test_end_to_end_offline(sandbox, board, fake_providers):
    """Fake models, real FFmpeg: both exports exist, 60-90 s, right size,
    with audio, burned subtitles and a passing verification report."""
    board["render"]["sizes"] = {"vertical": [180, 320], "horizontal": [320, 180]}
    # Pin the consent state so the test does not depend on the committed storyboard:
    # a script not yet approved exercises the DRAFT-overlay branch of the render.
    board["consent"].update(script_approved=False, likeness_approved=False)
    for s in board["shots"]:
        narration.generate(board, s)
        keyframes.generate(board, s)
    report = assemble.build(board)

    assert report["draft"] is True and report["likeness_shown"] is False
    for export, (w, h) in zip(report["exports"], [(180, 320), (320, 180)]):
        assert export["ok"], export["checks"]
        assert 60 <= export["duration_s"] <= 90
        assert (export["width"], export["height"]) == (w, h)
        path = Path(export["file"])
        path = path if path.is_absolute() else common.ROOT / path
        streams = common.probe(path)["streams"]
        assert {s["codec_type"] for s in streams} == {"video", "audio"}
    srt = (common.OUTPUTS / "final" / "subtitles_en.srt").read_text()
    assert board["shots"][0]["narration"]["en"].split()[0] in srt
    assert (common.OUTPUTS / "tmp" / "subs_vertical.ass").exists()
    assert any(l["event"] == "mix" for l in log_lines(sandbox))
