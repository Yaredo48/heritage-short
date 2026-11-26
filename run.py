#!/usr/bin/env python3
"""One entry point for every stage of the Heritage Short pipeline.

    python run.py film            # the whole pipeline, end to end (= make film)
    python run.py <command> -h    # help for one command

Every stage reads storyboard.json (validated first), writes into outputs/,
skips work whose inputs have not changed, and logs to runs.jsonl.
"""
import argparse
import importlib

# command -> (module that implements it, what it does)
COMMANDS = {
    "smoke":         ("pipeline.smoke",     "Call each provider once and log latency"),
    "validate":      ("pipeline.validate",  "Check storyboard.json against the schema"),
    "script":        ("pipeline.script",    "Draft storyboard.draft.json from story/notes.md with Gemini"),
    "narration":     ("pipeline.narration", "Stage 4: one Amharic narration file per shot (Gemini TTS)"),
    "timing":        ("pipeline.narration", "Show narration length against shot length"),
    "radio":         ("pipeline.radio",     "Radio cut: narration and score on black, with subtitles"),
    "refs":          ("pipeline.keyframes", "Reference-sheet candidates (character only with consent)"),
    "keyframes":     ("pipeline.keyframes", "Stage 1: one keyframe per shot (FLUX.2 klein)"),
    "kaggle-export": ("pipeline.kaggle_io", "Package Wan and ACE-Step jobs for the Kaggle notebooks"),
    "kaggle-import": ("pipeline.kaggle_io", "Bring Kaggle clips, music and logs back"),
    "shots":         ("pipeline.shots",     "Stage 2: one moving segment per shot (Wan clip or Ken Burns)"),
    "music":         ("pipeline.music",     "Stage 3: prepare the chosen score (or the temp pad)"),
    "assemble":      ("pipeline.assemble",  "Stage 5: edit, duck, subtitle, normalise, end card, 9:16 + 16:9"),
    "costs":         ("pipeline.costs",     "Summarise runs.jsonl into COSTS.md"),
    "langtest":      ("pipeline.langtest",  "E16: TTS intelligibility by ASR round trip (Amharic + 3 languages)"),
}
FILM = ["validate", "narration", "keyframes", "shots", "music", "assemble"]


def run_command(name, args):
    module = importlib.import_module(COMMANDS[name][0])
    module.main(name, args)


def main():
    parser = argparse.ArgumentParser(
        description="Heritage Short pipeline",
        epilog="\n".join(f"  {k:<14} {v[1]}" for k, v in COMMANDS.items()),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=[*COMMANDS, "film"])
    parser.add_argument("--shot", help="only this shot id, e.g. s03")
    parser.add_argument("--force", action="store_true", help="ignore the cache and regenerate")
    parser.add_argument("--zip", help="path to the Kaggle results zip (kaggle-import)")
    args = parser.parse_args()

    if args.command == "film":
        for name in FILM:
            print(f"\n=== {name} ===")
            run_command(name, args)
    else:
        run_command(args.command, args)


if __name__ == "__main__":
    main()
