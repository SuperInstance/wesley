# Wesley Architecture

## The loop

1. **Stream** (`scripts/wesley-stream.py`): picks a piece from the writing
   corpus, prompts Wesley (Ollama, granite3.1-dense:2b), saves his response,
   commits periodically. Runs continuously — this is Wesley "living."
2. **Night school** (runner + `scripts/wesley_night_school.py`): structured
   sessions. Wesley writes responses to assignments; one response goes to a
   cloud teacher (Cloudflare Workers AI, llama-3.1-8b) for a single
   actionable critique; lessons become prompt revisions and reflexes.
3. **Distillation** (see fleet repos: thought-amplifier): accumulated
   lessons are tested — if teaching improves the baseline, promote; if it
   regresses, gate and revert.

## Key lessons

- Overknowledge problem: teaching a model that already scores >0.85 hurts.
- Frame beats question (exp 088): casting > coaxing.
- Small models grow through reps, not scale.
