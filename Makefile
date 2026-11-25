# Heritage Short: one command per stage. `make film` runs the whole pipeline.
PY ?= .venv/bin/python
RUN = "$(PY)" run.py

.PHONY: help setup smoke validate script narration timing radio refs keyframes shots music \
        assemble film shot kaggle-export import costs test clean

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

setup:           ## create .venv and install requirements
	python3 -m venv .venv
	"$(PY)" -m pip install -r requirements.txt

smoke:           ## call each provider once, log latency
	$(RUN) smoke
validate:        ## check storyboard.json against the schema
	$(RUN) validate
script:          ## draft storyboard.draft.json with Gemini (never overwrites storyboard.json)
	$(RUN) script
narration:       ## Stage 4: Amharic narration per shot (Gemini TTS)
	$(RUN) narration
timing:          ## narration length vs shot length
	$(RUN) timing
radio:           ## radio cut for the first audience test
	$(RUN) radio
refs:            ## reference-sheet candidates
	$(RUN) refs
keyframes:       ## Stage 1: keyframes (FLUX.2 klein on Cloudflare)
	$(RUN) keyframes
shots:           ## Stage 2: moving segments (Wan clip if imported, else Ken Burns)
	$(RUN) shots
music:           ## Stage 3: chosen ACE-Step score, or the temp pad
	$(RUN) music
assemble:        ## Stage 5: both exports, verified
	$(RUN) assemble

film:            ## the whole pipeline, end to end
	$(RUN) film

shot:            ## regenerate one shot after editing it: make shot SHOT=s03
	@test -n "$(SHOT)" || (echo "usage: make shot SHOT=s03" && exit 1)
	$(RUN) validate
	$(RUN) narration --shot $(SHOT)
	$(RUN) keyframes --shot $(SHOT)
	$(RUN) shots --shot $(SHOT)
	$(RUN) assemble

kaggle-export:   ## package keyframes + jobs for the Kaggle notebooks
	$(RUN) kaggle-export
import:          ## bring Kaggle results back: make import ZIP=~/Downloads/heritage_results.zip
	$(RUN) kaggle-import --zip $(ZIP)

costs:           ## summarise runs.jsonl into COSTS.md
	$(RUN) costs
test:            ## offline tests (no API calls)
	"$(PY)" -m pytest -q

clean:           ## delete derived files only (model outputs are kept)
	rm -rf outputs/tmp outputs/shots/vertical outputs/shots/horizontal outputs/final/mix_*
