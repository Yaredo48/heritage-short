#!/usr/bin/env python3
"""One entry point for every stage of the Heritage Short pipeline.

    python run.py film            # the whole pipeline, end to end
    python run.py <command> -h    # help for one command
"""
import argparse
import importlib
import sys

# command -> (module that implements it, what it does, step that builds it)
COMMANDS = {
    "smoke":        ("pipeline.smoke",      "Call each provider once and log latency", 2),
    "validate":     ("pipeline.validate",   "Check storyboard.json against the schema", 3),
    "script":       ("pipeline.script",     "Draft storyboard.draft.json from story/notes.md with Gemini", 3),
    "narration":    ("pipeline.narration",  "Generate one Amharic narration file per shot", 4),
    "timing":       ("pipeline.narration",  "Show narration length against shot length", 4),
    "radio":        ("pipeline.radio",      "Narration over placeholder music on black", 4),
    "refs":         ("pipeline.refs",       "Generate reference-sheet candidates", 5),
    "keyframes":    ("pipeline.keyframes",  "Generate one keyframe per shot", 5),
    "kaggle-export":("pipeline.kaggle_io",  "Package Wan and ACE-Step jobs for Kaggle", 6),
    "kaggle-import":("pipeline.kaggle_io",  "Bring Kaggle outputs and logs back", 6),
    "shots":        ("pipeline.shots",      "One moving segment per shot (Wan clip or Ken Burns)", 7),
    "music":        ("pipeline.music",      "Prepare the chosen score", 7),
    "assemble":     ("pipeline.assemble",   "Edit, duck, subtitle, normalise, end card, both ratios", 8),
    "costs":        ("pipeline.costs",      "Summarise runs.jsonl into COSTS.md", 9),
}
FILM = ["validate", "narration", "keyframes", "shots", "music", "assemble"]


def run_command(name, args):
    module_name, _, step = COMMANDS[name]
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as err:
        if err.name == module_name:
            sys.exit(f"'{name}' is not built yet. It arrives in Step {step}.")
        raise
    module.main(name, args)


def main():
    parser = argparse.ArgumentParser(description="Heritage Short pipeline")
    parser.add_argument("command", choices=[*COMMANDS, "film"])
    parser.add_argument("--shot", help="only this shot id, e.g. s03")
    parser.add_argument("--force", action="store_true", help="ignore the cache")
    parser.add_argument("--zip", help="path to the Kaggle output zip (kaggle-import)")
    args = parser.parse_args()

    if args.command == "film":
        for name in FILM:
            print(f"\n=== {name} ===")
            run_command(name, args)
    else:
        run_command(args.command, args)


if __name__ == "__main__":
    main()
