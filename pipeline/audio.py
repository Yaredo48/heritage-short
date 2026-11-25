"""Small deterministic audio helpers (no model calls)."""
from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path

FRAME_S = 0.02  # analyse in 20 ms frames


def compress_pauses(src: Path, dst: Path, max_pause_s: float, threshold_db: float = -40.0,
                    edge_pause_s: float = 0.1) -> dict:
    """Shorten every silence longer than max_pause_s to max_pause_s.

    Gemini TTS put 0.5-1.1 s pauses between Amharic phrases, which made the
    film too long. Keeping half the allowed pause on each side of a cut keeps
    the breath natural. Leading/trailing silence is cut to edge_pause_s.
    Works on 16-bit mono WAV (what Gemini TTS returns).
    """
    with wave.open(str(src), "rb") as w:
        rate, width, channels = w.getframerate(), w.getsampwidth(), w.getnchannels()
        if width != 2 or channels != 1:
            raise ValueError(f"{src}: expected 16-bit mono WAV")
        samples = array("h", w.readframes(w.getnframes()))

    step = max(1, int(rate * FRAME_S))
    limit = 32768 * 10 ** (threshold_db / 20)
    silent = []
    for i in range(0, len(samples), step):
        chunk = samples[i:i + step]
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk)) if chunk else 0
        silent.append(rms < limit)

    keep = array("h")
    removed_frames, i, n = 0, 0, len(silent)
    while i < n:
        j = i
        while j < n and silent[j] == silent[i]:
            j += 1
        start, end = i * step, min(j * step, len(samples))
        run = samples[start:end]
        if silent[i]:
            at_edge = i == 0 or j == n
            allowed = int(rate * (edge_pause_s if at_edge else max_pause_s))
            if len(run) > allowed:
                half = allowed // 2
                if i == 0:
                    run = run[len(run) - allowed:]
                elif j == n:
                    run = run[:allowed]
                else:
                    run = run[:half] + run[len(run) - (allowed - half):]
                removed_frames += (end - start) - len(run)
        keep.extend(run)
        i = j

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(keep.tobytes())
    tmp.replace(dst)
    return {"in_s": round(len(samples) / rate, 3), "out_s": round(len(keep) / rate, 3),
            "removed_s": round(removed_frames / rate, 3)}
