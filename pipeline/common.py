"""Shared helpers for every stage: paths, secrets, the runs.jsonl log,
content hashing for the cache, retries, and small FFmpeg wrappers."""
from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
RUNS_LOG = ROOT / "runs.jsonl"
STORYBOARD = ROOT / "storyboard.json"

load_dotenv(ROOT / ".env")

# One id per invocation; `python run.py film` shares it across all stages.
RUN_ID = os.environ.setdefault(
    "HERITAGE_RUN_ID",
    datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6],
)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ModelCallError(RuntimeError):
    """A model call that failed for good (after retries, or not retryable)."""


# ---------- secrets ----------

def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name) or default
    if not value:
        raise SystemExit(f"Missing {name}. Put it in .env (see .env.example).")
    return value


# ---------- logging ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def log_event(event: str, stage: str, **fields) -> dict:
    """Append one JSON line to runs.jsonl. Never pass secrets in fields."""
    record = {"ts": now_iso(), "run_id": RUN_ID, "event": event, "stage": stage, **fields}
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


# ---------- hashing and cache ----------

def canonical_hash(obj) -> str:
    """Same content -> same hash, whatever the key order."""
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_path(stage_dir: str, name: str, key: str, ext: str) -> Path:
    """outputs/<stage_dir>/<name>_<first 12 chars of key>.<ext>"""
    folder = OUTPUTS / stage_dir
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{name}_{key[:12]}.{ext}"


def cache_hit(path: Path, stage: str, shot: str | None, key: str, force: bool = False) -> bool:
    if path.exists() and not force:
        log_event("cache_hit", stage, shot=shot, cache_key=key, output=str(path.relative_to(ROOT)))
        return True
    return False


# ---------- retries ----------

def call_with_retries(fn, *, stage: str, shot: str | None, provider: str, model: str,
                      params: dict, seed: int | None = None, attempts: int = 3,
                      cache_key: str | None = None, output: str | None = None):
    """Run fn() (ONE request) up to `attempts` times with exponential backoff.

    fn returns (result, meta); meta is merged into the log line (e.g. cost).
    Every attempt, failed or not, is one line in runs.jsonl.
    """
    common = dict(shot=shot, provider=provider, model=model, params=params, seed=seed,
                  cache_key=cache_key, output=output)
    for attempt in range(1, attempts + 1):
        t0 = time.perf_counter()
        try:
            result, meta = fn()
        except Exception as err:  # noqa: BLE001 - we log, classify, then re-raise
            latency = round(time.perf_counter() - t0, 3)
            status = getattr(getattr(err, "response", None), "status_code", None)
            retryable = status in RETRYABLE_STATUS or isinstance(
                err, (requests.ConnectionError, requests.Timeout))
            log_event("model_call", stage, **common, attempt=attempt, status="error",
                      http_status=status, latency_s=latency, error=str(err)[:300])
            if not retryable or attempt == attempts:
                raise ModelCallError(f"{provider}/{model} failed: {str(err)[:300]}") from err
            wait = 2 ** attempt + random.uniform(0, 1)
            print(f"  retry {attempt}/{attempts - 1} in {wait:.1f}s ({status or type(err).__name__})")
            time.sleep(wait)
        else:
            latency = round(time.perf_counter() - t0, 3)
            log_event("model_call", stage, **common, attempt=attempt, status="ok",
                      latency_s=latency, **meta)
            return result


def check_http(resp: requests.Response) -> requests.Response:
    """Raise with the response body attached, so the log shows the real reason."""
    if resp.status_code >= 400:
        raise requests.HTTPError(f"HTTP {resp.status_code}: {resp.text[:300]}", response=resp)
    return resp


# ---------- FFmpeg ----------

def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def duration_s(path: Path | str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True).stdout.strip()
    return float(out)
