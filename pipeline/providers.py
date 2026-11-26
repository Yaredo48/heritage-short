"""Thin clients for the hosted models. Each function makes ONE logical call
through call_with_retries, so every attempt lands in runs.jsonl."""
from __future__ import annotations

import base64
import io
import math
import os
import wave
from pathlib import Path

import requests
from PIL import Image

from .common import ModelCallError, call_with_retries, check_http, env

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
CF_BASE = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"

# Cloudflare list prices for FLUX.2 klein 4B (checked 2026-11-25):
# 26.05 neurons per output 512x512 tile, 5.37 per input tile; $0.011 per 1,000 neurons.
KLEIN_OUT_TILE, KLEIN_IN_TILE, USD_PER_NEURON = 26.05, 5.37, 0.011 / 1000


# ---------- Gemini text ----------

def gemini_text(prompt: str, *, stage: str, shot: str | None = None,
                json_mode: bool = False, temperature: float = 0.7,
                audio: bytes | None = None, audio_mime: str = "audio/wav") -> str:
    """Flash first; if it is still overloaded after retries (503 'high demand',
    seen in the smoke test on 2026-11-25), fall back to Flash-Lite once.
    With `audio`, the clip is sent with the prompt (used for transcription)."""
    primary = env("GEMINI_TEXT_MODEL", "gemini-3.8-flash")
    fallback = os.environ.get("GEMINI_TEXT_FALLBACK", "gemini-flash-lite-latest")
    try:
        return _gemini_text_once(primary, prompt, stage=stage, shot=shot,
                                 json_mode=json_mode, temperature=temperature,
                                 audio=audio, audio_mime=audio_mime)
    except ModelCallError as err:
        if not fallback or fallback == primary or "503" not in str(err):
            raise
        print(f"  {primary} overloaded; falling back to {fallback}")
        return _gemini_text_once(fallback, prompt, stage=stage, shot=shot,
                                 json_mode=json_mode, temperature=temperature,
                                 audio=audio, audio_mime=audio_mime)


def _gemini_text_once(model: str, prompt: str, *, stage: str, shot: str | None,
                      json_mode: bool, temperature: float,
                      audio: bytes | None = None, audio_mime: str = "audio/wav") -> str:
    key = env("GEMINI_API_KEY")

    def once():
        config = {"temperature": temperature}
        if json_mode:
            config["responseMimeType"] = "application/json"
        parts = [{"text": prompt}]
        if audio is not None:
            parts.insert(0, {"inline_data": {"mime_type": audio_mime,
                                             "data": base64.b64encode(audio).decode("ascii")}})
        body = {"contents": [{"role": "user", "parts": parts}],
                "generationConfig": config}
        resp = check_http(requests.post(
            f"{GEMINI_BASE}/models/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body, timeout=180))
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        usage = data.get("usageMetadata", {})
        return text, {"cost": {"input_tokens": usage.get("promptTokenCount"),
                               "output_tokens": usage.get("candidatesTokenCount"),
                               "tier": "free"}}

    return call_with_retries(once, stage=stage, shot=shot, provider="gemini", model=model,
                             params={"temperature": temperature, "json_mode": json_mode,
                                     "prompt_chars": len(prompt),
                                     "audio_bytes": len(audio) if audio is not None else 0})


# ---------- Gemini TTS (Interactions API) ----------

def _find_audio_b64(node):
    """Search the response for the base64 audio, whatever its exact nesting."""
    if isinstance(node, dict):
        kind = str(node.get("type", "")) + str(node.get("mime_type", "")) + str(node.get("mimeType", ""))
        if isinstance(node.get("data"), str) and "audio" in kind:
            return node["data"]
        for value in node.values():
            found = _find_audio_b64(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_audio_b64(value)
            if found:
                return found
    return None


def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def gemini_tts(text: str, *, style: str, voice: str, stage: str, shot: str | None = None,
               cache_key: str | None = None, output: str | None = None) -> bytes:
    """Returns WAV bytes (24 kHz mono 16-bit)."""
    model = env("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
    key = env("GEMINI_API_KEY")

    def once():
        body = {
            "model": model,
            "input": [{"type": "user_input", "content": [{
                "type": "text", "text": text,
                "annotations": [{"type": "speech_metadata", "style": style}]}]}],
            "response_format": {"type": "audio"},
            "generation_config": {"speech_config": [{"voice": voice}]},
        }
        resp = check_http(requests.post(
            f"{GEMINI_BASE}/interactions",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json=body, timeout=180))
        data = resp.json()
        audio_b64 = _find_audio_b64(data)
        if not audio_b64:
            raise ModelCallError(f"no audio in TTS response; top-level keys: {list(data)[:10]}")
        audio = base64.b64decode(audio_b64)
        if not audio.startswith(b"RIFF"):
            audio = _pcm_to_wav(audio)
        return audio, {"cost": {"input_chars": len(text), "tier": "free"}}

    return call_with_retries(once, stage=stage, shot=shot, provider="gemini", model=model,
                             params={"voice": voice, "style": style, "text_chars": len(text)},
                             cache_key=cache_key, output=output)


# ---------- Cloudflare Workers AI: FLUX.2 klein 4B ----------

def _small_png(path: Path | str, max_side: int = 448) -> bytes:
    """Cloudflare needs reference images smaller than 512x512."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def cloudflare_image(prompt: str, *, width: int, height: int, seed: int, stage: str,
                     shot: str | None = None, refs: list[str] | None = None,
                     cache_key: str | None = None, output: str | None = None) -> bytes:
    """Returns PNG/JPEG bytes from FLUX.2 klein 4B (4 fixed steps)."""
    account = env("CLOUDFLARE_ACCOUNT_ID")
    token = env("CLOUDFLARE_API_TOKEN")
    model = env("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-2-klein-4b")
    refs = list(refs or [])[:4]

    def once():
        # (None, value) tuples force multipart/form-data even without files.
        form = {"prompt": (None, prompt), "width": (None, str(width)),
                "height": (None, str(height)), "seed": (None, str(seed))}
        for i, ref in enumerate(refs):
            form[f"input_image_{i}"] = (Path(ref).name, _small_png(ref), "image/png")
        resp = check_http(requests.post(
            CF_BASE.format(account=account, model=model),
            headers={"Authorization": f"Bearer {token}"}, files=form, timeout=180))
        if resp.headers.get("content-type", "").startswith("image/"):
            image = resp.content
        else:
            data = resp.json()
            if data.get("success") is False:
                raise ModelCallError(f"Cloudflare error: {data.get('errors')}")
            b64 = (data.get("result") or {}).get("image") or data.get("image")
            if not b64:
                raise ModelCallError(f"no image in response; keys: {list(data)[:10]}")
            image = base64.b64decode(b64.split(",", 1)[-1])
        tiles = math.ceil(width / 512) * math.ceil(height / 512)
        neurons = tiles * KLEIN_OUT_TILE + len(refs) * KLEIN_IN_TILE
        return image, {"cost": {"neurons_est": round(neurons, 2),
                                "usd_list_est": round(neurons * USD_PER_NEURON, 6),
                                "tier": "free (10,000 neurons/day)"}}

    return call_with_retries(once, stage=stage, shot=shot, provider="cloudflare", model=model,
                             params={"width": width, "height": height, "steps": 4,
                                     "refs": len(refs), "prompt_chars": len(prompt)},
                             seed=seed, cache_key=cache_key, output=output)
