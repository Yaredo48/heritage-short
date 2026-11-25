"""Smoke test: call every hosted provider once, save what comes back,
and log latency to runs.jsonl. Run: python run.py smoke"""
from __future__ import annotations

import shutil
import time

from .common import OUTPUTS, ROOT, duration_s, log_event
from .providers import cloudflare_image, gemini_text, gemini_tts

AMHARIC_TEST = "ሰላም። ይህ የድምፅ ሙከራ ነው።"  # "Hello. This is a voice test."


def main(command, args):
    out = OUTPUTS / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    results = []

    def check(name, fn):
        t0 = time.perf_counter()
        try:
            detail = fn()
            results.append((name, "OK", round(time.perf_counter() - t0, 2), detail))
        except (Exception, SystemExit) as err:  # noqa: BLE001 - report every failure
            results.append((name, "FAIL", round(time.perf_counter() - t0, 2), str(err)[:160]))

    def ffmpeg_ok():
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError("ffmpeg/ffprobe not on PATH")
        return "ffmpeg and ffprobe found"

    def text_ok():
        reply = gemini_text("Reply with exactly one word: ready", stage="smoke", temperature=0)
        return f"reply: {reply.strip()[:40]!r}"

    def tts_ok():
        path = out / "tts_amharic.wav"
        path.write_bytes(gemini_tts(AMHARIC_TEST, style="calm, warm, unhurried", voice="Kore",
                                    stage="smoke", output=str(path.relative_to(ROOT))))
        return f"{path.relative_to(ROOT)} ({duration_s(path):.2f} s of audio)"

    def image_ok():
        path = out / "flux_klein_512.png"
        path.write_bytes(cloudflare_image(
            "a clay coffee pot (jebena) on a wooden table, soft morning light",
            width=512, height=512, seed=1, stage="smoke", output=str(path.relative_to(ROOT))))
        return f"{path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)"

    check("FFmpeg", ffmpeg_ok)
    check("Gemini text", text_ok)
    check("Gemini TTS (Amharic)", tts_ok)
    check("Cloudflare FLUX.2 klein", image_ok)

    print(f"\n{'provider':<26}{'result':<7}{'seconds':>8}  detail")
    for name, status, secs, detail in results:
        print(f"{name:<26}{status:<7}{secs:>8}  {detail}")
    log_event("smoke_summary", "smoke", results=[
        {"name": n, "status": s, "seconds": t} for n, s, t, _ in results])
    if any(status == "FAIL" for _, status, _, _ in results):
        raise SystemExit("\nSome checks failed. Paste this table to Claude.")
    print("\nAll providers work. Every call above is now a line in runs.jsonl.")
