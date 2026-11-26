"""Ceiling experiment (EXPERIMENTS.md E16): how intelligible is Gemini TTS in
Ethiopian and Horn-of-Africa languages? Measured without listeners by an ASR
round trip: TTS audio -> Gemini transcription -> character error rate (CER)
against the text that was spoken.

  1. Amharic: the 9 real narration files of the film (processed WAVs), each
     transcribed and compared with its shots[].narration.am line.
  2. Other languages: shot s01's English line is translated by Gemini into
     Tigrinya, Afaan Oromo and Somali, spoken by the same stock voice, then
     transcribed. English itself is the control: it shows the error floor of
     the round trip.

Caveats (also in EXPERIMENTS.md): the transcriber is the same model family as
the voice, so CER measures intelligibility *to Gemini*, not to people; and the
translations themselves are not checked by a speaker. A high CER is a strong
warning; a low CER is not proof of good pronunciation.

Every result is cached in outputs/langtest/ by a hash of its inputs, so a rerun
makes no new calls. Run: python run.py langtest
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from . import common
from .common import canonical_hash, cache_hit, env, file_hash, log_event, rel, write_atomic
from .narration import narration_path
from .providers import gemini_text, gemini_tts
from .validate import load_storyboard

STAGE = "langtest"
LANGS = {  # code: (name, script)
    "en": ("English", "Latin"),
    "ti": ("Tigrinya", "Ge'ez (Ethiopic)"),
    "om": ("Afaan Oromo", "Latin (Qubee)"),
    "so": ("Somali", "Latin"),
}
AMHARIC = ("Amharic", "Ge'ez (Ethiopic)")
SOURCE_SHOT = "s01"


# ---------- scoring ----------

def normalise(text: str) -> str:
    """Compare letters only: drop punctuation (including Ethiopic ። ፣ ፤ …),
    whitespace and case, and use one Unicode form."""
    text = unicodedata.normalize("NFC", text).lower()
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in "LN")


# Ethiopic letters that are pronounced the same in modern Amharic and Tigrinya and are
# routinely interchanged in writing (e.g. ሕልም / ህልም, ሠ / ሰ, ዕድል / እድል). Each maps a whole
# 8-letter series onto its common counterpart, order by order.
HOMOPHONE_SERIES = {0x1210: 0x1200, 0x1280: 0x1200,   # ሐ, ኀ -> ሀ
                    0x1220: 0x1230,                   # ሠ -> ሰ
                    0x12D0: 0x12A0,                   # ዐ -> አ
                    0x1340: 0x1338}                   # ፀ -> ጸ


def fold_homophones(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        for src, dst in HOMOPHONE_SERIES.items():
            if src <= code < src + 8:
                ch = chr(dst + code - src)
                break
        out.append(ch)
    return "".join(out)


def non_script_letters(text: str, script_prefix: str = "ETHIOPIC") -> str:
    """Letters that are not in the expected script (e.g. Cyrillic inside Ge'ez)."""
    return "".join(ch for ch in normalise(text)
                   if not unicodedata.name(ch, "").startswith(script_prefix) and not ch.isdigit())


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(reference: str, hypothesis: str, fold: bool = False) -> float:
    ref, hyp = normalise(reference), normalise(hypothesis)
    if fold:
        ref, hyp = fold_homophones(ref), fold_homophones(hyp)
    return round(edit_distance(ref, hyp) / max(len(ref), 1), 4)


# ---------- cached model steps ----------

def _cached_json(name: str, key: str, shot: str | None, make) -> dict:
    path = common.cache_path(STAGE, name, key, "json")
    if cache_hit(path, STAGE, shot, key):
        return json.loads(path.read_text(encoding="utf-8"))
    data = make(path)
    write_atomic(path, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    return data


def transcribe(wav: Path, language: tuple[str, str], shot: str | None) -> str:
    name, script = language
    prompt = (f"Transcribe this {name} speech exactly as spoken, in {name} written in its standard "
              f"{script} script. Output only the transcription: no translation, no notes.")
    model = env("GEMINI_TEXT_MODEL", "gemini-3.8-flash")
    key = canonical_hash({"audio": file_hash(wav), "prompt": prompt, "model": model})
    tag = f"asr_{shot or 'x'}_{name.split()[0].lower()}"
    data = _cached_json(tag, key, shot, lambda path: {"text": gemini_text(
        prompt, stage=STAGE, shot=shot, temperature=0, audio=wav.read_bytes()).strip()})
    return data["text"]


def translate(english: str, code: str) -> str:
    name, script = LANGS[code]
    prompt = (f"Translate this sentence into {name}, written in {script} script. "
              f"Output only the translation.\n\n{english}")
    key = canonical_hash({"prompt": prompt, "model": env("GEMINI_TEXT_MODEL", "gemini-3.8-flash")})
    data = _cached_json(f"mt_{code}", key, SOURCE_SHOT, lambda path: {"text": gemini_text(
        prompt, stage=STAGE, shot=SOURCE_SHOT, temperature=0).strip()})
    return data["text"]


def speak(text: str, code: str, board: dict) -> Path:
    voice = board["voice"]["voice"]
    style = f"{LANGS[code][0]}, spoken slowly and warmly"
    key = canonical_hash({"text": text, "voice": voice, "style": style,
                          "model": env("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")})
    path = common.cache_path(STAGE, f"tts_{code}", key, "wav")
    if not cache_hit(path, STAGE, SOURCE_SHOT, key):
        audio = gemini_tts(text, style=style, voice=voice, stage=STAGE, shot=SOURCE_SHOT,
                           cache_key=key, output=rel(path))
        write_atomic(path, audio)
    return path


# ---------- the experiment ----------

def run(board: dict) -> dict:
    rows = []
    for shot in board["shots"]:
        wav = narration_path(board, shot)
        if not wav.exists():
            raise SystemExit(f"{shot['id']}: narration missing; run `make narration` first")
        heard = transcribe(wav, AMHARIC, shot["id"])
        ref = shot["narration"]["am"]
        rows.append({"lang": "am", "shot": shot["id"], "reference": ref, "transcript": heard,
                     "cer": cer(ref, heard), "cer_homophones_folded": cer(ref, heard, fold=True)})
    english = next(s for s in board["shots"] if s["id"] == SOURCE_SHOT)["narration"]["en"]
    for code in LANGS:
        text = english if code == "en" else translate(english, code)
        wav = speak(text, code, board)
        heard = transcribe(wav, LANGS[code], SOURCE_SHOT)
        row = {"lang": code, "shot": SOURCE_SHOT, "reference": text, "transcript": heard,
               "cer": cer(text, heard)}
        if code == "ti":  # Ge'ez script: fold homophones, and flag foreign letters in the text itself
            row["cer_homophones_folded"] = cer(text, heard, fold=True)
            row["foreign_letters_in_reference"] = non_script_letters(text)
        rows.append(row)
    am = [r["cer"] for r in rows if r["lang"] == "am"]
    summary = {
        "models": {"asr_and_translation": env("GEMINI_TEXT_MODEL", "gemini-3.8-flash"),
                   "tts": env("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts"), "voice": board["voice"]["voice"]},
        "amharic_narration": {"lines": len(am), "mean_cer": round(sum(am) / len(am), 4),
                              "mean_cer_homophones_folded": round(sum(
                                  r["cer_homophones_folded"] for r in rows if r["lang"] == "am") / len(am), 4),
                              "max_cer": max(am), "worst_shot": max(
                                  (r for r in rows if r["lang"] == "am"), key=lambda r: r["cer"])["shot"]},
        "s01_line": {r["lang"]: r["cer"] for r in rows if r["shot"] == SOURCE_SHOT and r["lang"] != "am"}
                    | {"am": next(r["cer"] for r in rows if r["lang"] == "am" and r["shot"] == SOURCE_SHOT)},
        "rows": rows,
    }
    out = common.out_dir(STAGE) / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_event("langtest", STAGE, output=rel(out), amharic_mean_cer=summary["amharic_narration"]["mean_cer"],
              s01_cer=summary["s01_line"])
    return summary


def main(command, args):
    board = load_storyboard(stage=STAGE)
    summary = run(board)
    print(f"\n{'lang':<5}{'shot':<6}{'CER':>7}{'folded':>8}  transcript")
    for r in summary["rows"]:
        folded = r.get("cer_homophones_folded")
        print(f"{r['lang']:<5}{r['shot']:<6}{r['cer']:>7.3f}{'' if folded is None else f'{folded:>8.3f}':>8}  "
              f"{r['transcript'][:60]}")
    a = summary["amharic_narration"]
    print(f"\nAmharic narration: mean CER {a['mean_cer']:.3f} (homophones folded {a['mean_cer_homophones_folded']:.3f}), "
          f"max {a['max_cer']:.3f} ({a['worst_shot']})")
    print("s01 line by language:", summary["s01_line"])
    print(f"summary: {rel(common.out_dir(STAGE) / 'summary.json')}")
