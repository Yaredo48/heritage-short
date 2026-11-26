# Submission

**What the form asks for:** one link, the public GitHub repository, "showcasing your original work … with clear documentation of your contributions and the project's implementation".

**Submit:** `https://github.com/Yaredo48/heritage-short`

The graders read code, text and logs; they do not open the audio, video or images. The README's section **"For assessors: where each criterion is evidenced"** maps every criterion to its files, and the **"Contributions"** section states who did what.

## Grading and where it is answered

| Criterion | Points | Evidence | Honest state |
|---|---|---|---|
| Software engineering and reproducibility | 28 | validated contract, content-hash cache, retries, `runs.jsonl`, 25 tests, CI workflow, clean-clone `make film` | complete |
| Documentation | 14 | README, ARCHITECTURE.md, technical PDF, setup guide | complete |
| Design thinking and audience | 14 | DESIGN.md: audience before generation, a reason per shot, questionnaires | **user tests not run** (stated) |
| Experimentation and iteration | 14 | EXPERIMENTS.md E01–E10, E15, E16 | 12 run; Kaggle E11–E14 not run |
| Troubleshooting and persistence | 14 | FAILURES.md F01–F11 | complete |
| Measurement | 8 | COSTS.md (from the log), `report.json`, `langtest/summary.json` | no GPU minutes (Kaggle not run); no frontier access |
| Consent, labelling and licences | 8 | ETHICS.md: written consent 26 Nov, consent gate, licences, labelling | complete; film not posted publicly (consent scope) |

## Before you press submit

- [ ] `git status` is clean and `main` is pushed (the *Actions* tab shows the `tests` workflow green).
- [ ] The repository is **public**. Open the link in a private browser window.
- [ ] Reread `docs/INTERVIEW_PREP.md` if an interview follows.

## Optional material in the repository

`docs/REPORT.md` / `docs/REPORT.pdf` (a reflective report), `docs/WALKTHROUGH.md` (a 5-minute recording plan) and `docs/POST_NOTES.md` were prepared for the brief's second assignment (film, walkthrough, post). The current form does not ask for them. If a separate form does, remember that her consent covers private evaluation only: share files privately with the assessors, and do not post the film publicly.
