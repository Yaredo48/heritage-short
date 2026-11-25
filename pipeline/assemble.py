"""Stage 5, assembly (FFmpeg only, no model calls).

  1. timeline from the narration (narration.timeline)
  2. audio: each narration line placed at its shot's start + lead-in, the score
     looped/trimmed under it, ducked with sidechaincompress, then a two-pass
     loudnorm to -14 LUFS / -1 dBTP
  3. picture: shot segments joined with crossfades, fade in/out, an AI
     disclosure end card, burned-in English subtitles, and a DRAFT mark while
     the script is not approved
  4. export 9:16 and 16:9 MP4 (H.264 + AAC), then verify duration, size,
     streams and loudness into outputs/final/report.json

Run: python run.py assemble
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import common
from .common import canonical_hash, ffmpeg, file_hash, log_event, probe, rel
from .music import PRE_MIX_LUFS, match_loudness, measure_lufs, prepare
from .narration import film_length, timeline
from .shots import segment
from .validate import MAX_TOTAL_S, MIN_TOTAL_S, load_storyboard

STAGE = "assemble"
CHARS_PER_LINE = {"vertical": 36, "horizontal": 42, "srt": 42}
SUB_STYLE = {  # font px, side margin, bottom margin (vertical keeps clear of platform buttons)
    "vertical": (48, 70, 420),
    "horizontal": (48, 160, 70),
}
FONTS = ["/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf"]


# ---------- subtitles ----------

def cues(board: dict, rows: list[dict], width: int) -> list[tuple[float, float, list[str]]]:
    """(start, end, lines) per cue: at most two lines of `width` chars, timed to
    the narration of each shot; long lines are split in proportion to length."""
    out = []
    lead = board["render"]["lead_in_s"]
    for r in rows:
        lines = balanced_wrap(r["shot"]["narration"]["en"], width)
        groups = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        total_chars = sum(len(" ".join(g)) for g in groups)
        t = r["start"] + lead
        speech = max(r["narr_s"], 1.5)
        for g in groups:
            share = speech * len(" ".join(g)) / total_chars
            out.append((round(t, 3), round(t + share + (0.3 if g is groups[-1] else 0), 3), g))
            t += share
    return out


def balanced_wrap(text: str, width: int) -> list[str]:
    """Wrap to at most `width` chars per line, using as few two-line cues as
    possible and lines of similar length (no single orphan word on a cue)."""
    lines = textwrap.wrap(text, width=width)
    cues_needed = math.ceil(len(lines) / 2)
    for w in range(math.ceil(len(text) / (2 * cues_needed)), width + 1):
        candidate = textwrap.wrap(text, width=w)
        if len(candidate) <= 2 * cues_needed:
            return candidate
    return lines


def ts(seconds: float, sep: str = ",", cs: bool = False) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if cs:  # ASS: h:mm:ss.cc
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)):03d}"


def write_srt(items, path: Path) -> None:
    blocks = [f"{i}\n{ts(a)} --> {ts(b)}\n" + "\n".join(lines)
              for i, (a, b, lines) in enumerate(items, 1)]
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def write_ass(items, path: Path, w: int, h: int, aspect: str) -> None:
    size, side, bottom = SUB_STYLE[aspect]
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans,{size},&H00FFFFFF,&H000000FF,&H00101010,&H78000000,0,0,0,0,100,100,0,0,1,3,1,2,{side},{side},{bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = [f"Dialogue: 0,{ts(a, cs=True)},{ts(b, cs=True)},Default,,0,0,0,," + r"\N".join(lines)
              for a, b, lines in items]
    path.write_text(head + "\n".join(events) + "\n", encoding="utf-8")


# ---------- still cards (Pillow, so no font paths inside FFmpeg filters) ----------

def font(size: int):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size=size)


def end_card(board: dict, w: int, h: int, path: Path) -> None:
    img = Image.new("RGB", (w, h), (20, 13, 8))
    draw = ImageDraw.Draw(img)
    lines = board["render"]["end_card_lines"]
    big, small = font(int(min(w, h) * 0.075)), font(int(min(w, h) * 0.04))
    sizes = [(big if i == 0 else small) for i in range(len(lines))]
    heights = [draw.textbbox((0, 0), t, font=f)[3] for t, f in zip(lines, sizes)]
    gap = int(min(w, h) * 0.03)
    y = (h - sum(heights) - gap * (len(lines) - 1)) // 2
    for text, f, lh in zip(lines, sizes, heights):
        tw = draw.textlength(text, font=f)
        colour = (240, 228, 210) if f is big else (200, 188, 170)
        draw.text(((w - tw) / 2, y), text, font=f, fill=colour)
        y += lh + gap
    img.save(path)


def draft_mark(w: int, h: int, path: Path) -> None:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    f = font(int(min(w, h) * 0.028))
    text = "DRAFT - pending family approval"
    tw = draw.textlength(text, font=f)
    draw.text((w - tw - int(w * 0.05), int(h * 0.06)), text, font=f, fill=(255, 255, 255, 150))
    img.save(path)


# ---------- audio ----------

def limiter(mix: dict) -> str:
    """Optional gentle peak limiter before loudnorm. Without it, linear loudnorm
    cannot reach -14 LUFS under the true-peak ceiling (EXPERIMENTS.md E09)."""
    if mix.get("pre_limiter_db") is None:
        return ""
    return f",alimiter=limit={10 ** (mix['pre_limiter_db'] / 20):.4f}:attack=5:release=80:level=disabled"


def mix_audio(board: dict, rows: list[dict], total: float) -> tuple[Path, dict, str]:
    score, source = prepare(board)
    mix = board["mix"]
    lead = board["render"]["lead_in_s"]
    key = canonical_hash({"narr": [(file_hash(r["narration"]), r["start"]) for r in rows],
                          "score": file_hash(score), "mix": mix, "lead": lead, "total": total})
    final_dir = common.out_dir("final")
    path = final_dir / f"mix_{key[:12]}.wav"
    if path.exists():
        return path, json.loads(path.with_suffix(".json").read_text()), source

    tmp = common.out_dir("tmp")
    inputs, chains = [], []
    for i, r in enumerate(rows):  # bring each line to the same loudness, then place it
        levelled = tmp / f"narr_{r['id']}.wav"
        match_loudness(r["narration"], levelled)
        inputs += ["-i", str(levelled)]
        ms = int(round((r["start"] + lead) * 1000))
        chains.append(f"[{i}:a]adelay={ms}|{ms}[n{i}]")
    n = len(rows)
    inputs += ["-stream_loop", "-1", "-i", str(score)]
    fade_out = max(total - 3.5, 0)
    graph = ";".join(chains + [
        "".join(f"[n{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{total:.3f},asplit=2[voice][key]",
        f"[{n}:a]atrim=0:{total:.3f},afade=t=in:d=2,afade=t=out:st={fade_out:.3f}:d=3.5,"
        f"volume={mix['music_gain_db']}dB[music]",
        f"[music][key]sidechaincompress=threshold={mix['duck_threshold']}:ratio={mix['duck_ratio']}:"
        f"attack={mix['duck_attack_ms']}:release={mix['duck_release_ms']}[ducked]",
        "[voice][ducked]amix=inputs=2:normalize=0" + limiter(mix) + "[out]"])
    raw = tmp / "mix_raw.wav"
    ffmpeg(*inputs, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", "-ac", "2", str(raw))

    # Two-pass loudnorm: measure, then apply with the measured values (linear mode).
    m = measure_lufs(raw)
    ln = (f"loudnorm=I={mix['target_lufs']}:TP={mix['true_peak_db']}:LRA=11:"
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:linear=true")
    ffmpeg("-i", str(raw), "-af", ln, "-ar", "48000", "-ac", "2", str(path))
    stats = {"before": m, "after": measure_lufs(path), "score": rel(score), "score_source": source}
    path.with_suffix(".json").write_text(json.dumps(stats, indent=2))
    log_event("mix", STAGE, output=rel(path), **stats)
    return path, stats, source


# ---------- picture + export ----------

def render(board: dict, rows: list[dict], aspect: str, audio: Path, total: float, out: Path) -> None:
    w, h = board["render"]["sizes"][aspect]
    fps, fade = board["render"]["fps"], board["render"]["transition_s"]
    work = common.out_dir("tmp")
    card, mark, subs = work / f"endcard_{aspect}.png", work / f"draft_{aspect}.png", work / f"subs_{aspect}.ass"
    end_card(board, w, h, card)
    write_ass(cues(board, rows, CHARS_PER_LINE[aspect]), subs, w, h, aspect)
    draft = not board["consent"]["script_approved"]
    if draft:
        draft_mark(w, h, mark)

    segs = [segment(board, r, aspect) for r in rows]
    inputs = []
    for s in segs:
        inputs += ["-i", str(s)]
    n = len(segs)
    inputs += ["-loop", "1", "-t", f"{board['render']['end_card_s'] + fade:.3f}", "-i", str(card)]
    if draft:
        inputs += ["-loop", "1", "-i", str(mark)]
    inputs += ["-i", str(audio)]

    norm = ",".join(["settb=AVTB", f"fps={fps}", f"scale={w}:{h}", "setsar=1", "format=yuv420p"])
    chains = [f"[{i}:v]{norm}[v{i}]" for i in range(n + 1)]
    prev, offset = "v0", 0.0
    for i in range(1, n + 1):  # crossfade into each next shot, and finally into the end card
        offset += rows[i - 1]["dur"]
        chains.append(f"[{prev}][v{i}]xfade=transition=fade:duration={fade}:offset={offset:.3f}[x{i}]")
        prev = f"x{i}"
    chains.append(f"[{prev}]fade=t=in:d=0.8,fade=t=out:st={total - 1:.3f}:d=1,"
                  f"ass={subs.name}[sub]")
    if draft:
        chains.append(f"[{n + 1}:v]format=rgba[mark];[sub][mark]overlay=0:0:shortest=1,format=yuv420p[vout]")
    else:
        chains.append("[sub]format=yuv420p[vout]")
    audio_index = n + 2 if draft else n + 1
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-filter_complex", ";".join(chains), "-map", "[vout]", "-map", f"{audio_index}:a",
           "-t", f"{total:.3f}", "-r", str(fps), "-c:v", "libx264", "-crf", "20", "-preset", "medium",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           "-metadata", "comment=Made with AI: FLUX.2 klein images, Gemini TTS narration, generated score",
           str(out)]
    subprocess.run(cmd, check=True, cwd=work)  # cwd so the ass filter needs no path escaping


def verify(board: dict, path: Path, aspect: str) -> dict:
    info = probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"])
    w, h = board["render"]["sizes"][aspect]
    loud = measure_lufs(path)
    checks = {
        "duration_60_90": MIN_TOTAL_S <= dur <= MAX_TOTAL_S,
        "size": [v["width"], v["height"]] == [w, h],
        "h264": v["codec_name"] == "h264",
        "aac_audio": bool(a) and a[0]["codec_name"] == "aac",
        "loudness_within_1lu": abs(loud["input_i"] - board["mix"]["target_lufs"]) <= 1.0,
        "true_peak_ok": loud["input_tp"] <= board["mix"]["true_peak_db"] + 0.5,
    }
    return {"file": rel(path), "duration_s": round(dur, 2), "width": v["width"], "height": v["height"],
            "fps": v["r_frame_rate"], "lufs": loud["input_i"], "true_peak_db": loud["input_tp"],
            "checks": checks, "ok": all(checks.values())}


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]


def build(board: dict) -> dict:
    """Mix, render both aspect ratios, verify. Returns the report."""
    rows = timeline(board)
    total = round(film_length(board, rows), 3)
    if not MIN_TOTAL_S <= total <= MAX_TOTAL_S:
        raise SystemExit(f"film would be {total:.1f}s; must be {MIN_TOTAL_S}-{MAX_TOTAL_S}s. "
                         f"Adjust shot durations or narration (see `make timing`).")
    audio, stats, source = mix_audio(board, rows, total)
    print(f"  mix: {rel(audio)} ({stats['after']['input_i']} LUFS, score = {source})")
    final = common.out_dir("final")
    write_srt(cues(board, rows, CHARS_PER_LINE["srt"]), final / "subtitles_en.srt")
    report = {"title": board["title"], "version": board["version"], "length_s": total,
              "score_source": source, "draft": not board["consent"]["script_approved"],
              "likeness_shown": board["consent"]["likeness_approved"], "exports": []}
    for aspect in board["render"]["sizes"]:
        out = final / f"{slug(board['title'])}_{aspect}.mp4"
        render(board, rows, aspect, audio, total, out)
        result = verify(board, out, aspect)
        report["exports"].append(result)
        print(f"  {aspect}: {result['file']} {result['width']}x{result['height']} "
              f"{result['duration_s']}s {result['lufs']} LUFS  checks {'OK' if result['ok'] else result['checks']}")
    (final / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    log_event("stage_done", STAGE, **report)
    return report


def main(command, args):
    report = build(load_storyboard(stage=STAGE))
    source = report["score_source"]
    if source == "placeholder":
        print("  note: the score is still the placeholder pad; choose an ACE-Step candidate before release")
    if report["draft"]:
        print("  note: DRAFT mark is on because consent.script_approved is false")
    if not all(e["ok"] for e in report["exports"]):
        raise SystemExit("verification failed; see outputs/final/report.json")
