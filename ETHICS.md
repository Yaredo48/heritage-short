# ETHICS

## 1. Consent

| Person | What is generated of them | How consent was given | Date | Script approved |
|---|---|---|---|---|
| My mother (A. A.) | An AI-generated woman representing her, seen from behind and through her hands (shots s04, s06, s07); no face is generated. She is not impersonated or voiced. | Written consent statement, confirmed by her (text below; the signed original with her full name is kept privately by me, not in this public repository) | 26 Nov 2026 | Yes: she reviewed the intended use and agreed. The statement does not list the narration lines one by one |

Consent will be obtained before generating or publishing AI representations of my mother's likeness. Her approval of the narration will also be requested before final production.

**What she agreed to (26 Nov 2026).** In a written statement she confirmed that she:
- understands the project uses AI to make a short video with an AI-generated representation of her likeness;
- was told its purpose and how her likeness would be used;
- understands the video is AI-generated, not a recording of her;
- voluntarily gives permission for her likeness to be used **for this educational assignment and its private evaluation by the relevant assessors**;
- knows she can ask questions and withdraw permission before the final submission;
- reviewed the intended use and agrees to participate.

Her exact wording, full name and confirmation are in the signed statement I keep privately. It is not reproduced in this public repository, to respect the private scope she agreed to.

**What this consent covers, and how the project stays inside it:**
- **Scope: the educational assignment and its private evaluation by the assessors.** The film is therefore **not posted, shared or promoted on any platform**.
- **The public repository.** The assignment is submitted as a public GitHub repository, and the brief asks for generated outputs to be kept in it so the run can be inspected. Those files (keyframes, narration, the two MP4s) are therefore publicly reachable, although the graders read code and text and do not open them. They contain **no face, no name and no identifying detail**: she appears only from behind and through her hands, and the voice is a stock AI voice. If she objects to these repository copies, they will be removed from the repository and its history.
- **Likeness.** Her consent would allow an AI face representing her. I chose **not** to use it: every generated image is also committed to this *public* repository, so the film keeps the no-face version (`consent.likeness_approved` stays `false`). Nothing identifiable of her is public, and every use stays within what she agreed to.
- **Script.** She reviewed the intended use and agreed, so `consent.script_approved` is now `true` and the DRAFT mark is removed. Her statement approves the project as a whole; it does not quote each narration line.
- **Withdrawal.** She can withdraw before the final submission. If she does, the film is not submitted and this record is updated.

**How the pipeline enforces this** (so the record above is not just a promise):

- `storyboard.json → consent.likeness_approved` is `false`. While it is false, the three shots that show her (s04, s06, s07) are generated from their `no_face_prompt` (seen from behind, or hands only), the character reference sheet is never generated, and the Wan motion prompts for those shots ask for the face to stay hidden. `runs.jsonl` logs a `consent_gate` line each time.
- The validator refuses `likeness_approved: true` while the row above still says *Pending*. Consent has to be written here first.
- `consent.script_approved` is `false`, so both exports carry a visible **DRAFT – pending family approval** mark and must not be published.
- One no-face prompt still showed her profile on the first attempt (s04, EXPERIMENTS.md E05). It was rewritten before anything was published. Every character keyframe is checked by eye for a visible face.

**To record consent** (fill in, then flip the flags):

> On [date], I showed my mother [the storyboard / the radio cut / the draft film] [in person / by phone] and explained that an AI model would generate a picture of a woman representing her, which would not be a photograph of her, and that the film would be shared [with family on Telegram / publicly on …]. She [agreed / agreed with these conditions: …]. She approved the narration text [as is / with these changes: …].

The people in the background of shots (children, family hands) are generated and represent no specific real person.

## 2. Voice

The narration uses a **stock Gemini TTS voice ("Charon")**. My mother's voice is not recorded, sampled or cloned, and no real person's voice is imitated. The narrator speaks as her child, in words taken from my own story notes.

## 3. Licences

| Component | Used for | Licence / terms | Output use |
|---|---|---|---|
| FLUX.2 klein 4B (Black Forest Labs) via Cloudflare Workers AI | keyframes, reference sheet | Apache 2.0 (4B model), Cloudflare Workers AI terms | allowed; the 9B variant is non-commercial and is **not** used |
| Gemini 3.8 Flash TTS / Flash (Google) via Gemini API free tier | narration, script draft | Gemini API terms; free-tier inputs may be used by Google to improve products | allowed; only story text from my notes is sent, no private details |
| Wan 2.2 TI2V-5B (Wan-AI) on Kaggle | moving shots | Apache 2.0 | allowed |
| ACE-Step 1.5 on Kaggle | score | MIT; trained on licensed, royalty-free and synthetic data; outputs usable commercially | allowed |
| FFmpeg | assembly, temp music pad | LGPL/GPL (tool only) | output not encumbered |
| Noto Sans | subtitles, end card | SIL Open Font License | allowed |
| Kaggle notebooks | GPU time | Kaggle terms (free weekly quota) | n/a |

## 4. Labelling plan

- The film ends on a card: "Made with AI: images, voice and music were generated by AI models". The MP4 metadata comment says the same.
- Reconstructed scenes are illustrations, not photographs or archive footage, and are never described as real.
- **No public posting.** Her consent covers the assignment and its private evaluation, so the film is not published on any platform. It is shared only privately with the assessors. If she later agrees to a public post, the platform's AI-content label (YouTube "Altered or synthetic content", TikTok "AI-generated content", Meta "AI info") will be switched on.
- No watermark or provenance metadata added by a provider is removed.

## 5. Private data

Private details (full names, home address, private conversations, other sensitive family information) are kept out of every prompt sent to a free endpoint. The prompts contain only the places named in my notes (Sheka Zone, Yeki Woreda) and general descriptions. The full prompts are in `storyboard.json`, so anyone can check this.
