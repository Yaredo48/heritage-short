"""Shared fixtures: a sandboxed outputs/ and runs.jsonl, and fake providers so
tests never call an API (and never spend free-tier quota)."""
import copy
import io
import json
import math
import wave
from array import array

import pytest
from PIL import Image

from pipeline import common
from pipeline.validate import STORYBOARD


@pytest.fixture
def board():
    return copy.deepcopy(json.loads(STORYBOARD.read_text(encoding="utf-8")))


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point every stage at a temp outputs/ folder and a temp runs.jsonl."""
    monkeypatch.setattr(common, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(common, "RUNS_LOG", tmp_path / "runs.jsonl")
    return tmp_path


def log_lines(sandbox):
    path = sandbox / "runs.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def fake_wav(seconds=3.0, pause_at=1.0, pause_s=1.2, rate=24000) -> bytes:
    """A tone with one long silent pause in it, like a TTS line."""
    samples = array("h")
    for i in range(int(seconds * rate)):
        t = i / rate
        silent = pause_at <= t < pause_at + pause_s
        samples.append(0 if silent else int(8000 * math.sin(2 * math.pi * 220 * t)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


def fake_png(colour=(120, 80, 40), size=(256, 256)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def fake_providers(monkeypatch):
    """Replace the hosted models; record every call."""
    calls = {"image": [], "tts": []}

    def image(prompt, **kw):
        calls["image"].append({"prompt": prompt, **kw})
        return fake_png()

    def tts(text, **kw):
        calls["tts"].append({"text": text, **kw})
        return fake_wav()

    monkeypatch.setattr("pipeline.keyframes.cloudflare_image", image)
    monkeypatch.setattr("pipeline.narration.gemini_tts", tts)
    return calls
