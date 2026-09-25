# Heidi Health pre-visit intake agent

A patient-facing voice agent on Cartesia Line for the FDE take-home. The clinic dials the patient's number before an appointment; the agent confirms it is speaking with that patient, collects reason for visit, medications, allergies and history, reads everything back, and records a structured summary for the clinician. It never diagnoses or gives advice, escalates red-flag symptoms to a human, and lets the patient end the call at any point with a partial record saved.

**Start at [INDEX.md](INDEX.md)** for links to the two PDF deliverables, the call recording, and the code.

Evaluation lives in `evals/` and produces real numbers on the agent. See `report/evaluation_report.pdf` (or `EVAL.md`, the long form) for the strategy and results, and `report/agent_notes.pdf` (or `NOTES.md`) for known weaknesses.

**Final full-set result (version 6, 18 cases × 10 runs): 177 of 180 runs pass every check, 0 safety-critical failures, 15 of 18 cases at 10/10, 1 run unjudged.** Measured on the agent's reasoning in text; a 72-clip audio set covers speech-to-text of drug names across six accents, and the rest of the audio path is the stated gap.

## Layout

```
main.py                    Line entry point: one session per call, build the agent, hand Line the guarded callable
intake/
  config.py                model, provider options, retry and timing settings, all from the environment
  prompt.py                system prompt + introduction, with a note on which failure produced each rule
  session.py               per-call state: expected patient, confirmation, escalation, record; call log
  patients.py              patient fixture lookup by phone number or id
  factory.py               build_agent(): prompt + tools + session -> LlmAgent (shared with the harness)
  guards.py                dead-air guard and call logging around the agent
  tools/
    __init__.py            build_tools(session): binds the four tools to one call
    confirm.py             confirm_patient     identity gate: the clinic dialled the number on file, a yes is trusted
    lookup.py              lookup_medication   normalise a spoken drug name, flag sound-alikes
    record.py              record_intake       save the summary; refuses if unverified
    escalate.py            escalate_to_human   red-flag nurse callback
    formulary.py           61-entry demo drug list with aliases and sound-alike groups
    schema.py              the record schema (TypedDicts) the model fills in
data/patients.json         three fake patients
data/medications.json      the formulary data
data/intakes/              recorded intake summaries (one JSON per call)
logs/calls.jsonl           structured call log: user text, agent text, every tool call with arguments
evals/
  simulate.py              drives the agent in-process (scripted or LLM-persona patient), no server or audio
  grade.py                 deterministic checks: accuracy, fabrication, safety screen, escalation, gate, tools, drive, case rules
  judge.py                 two-pass LLM safety judge with a 20-item calibration set
  normalize.py             dose, frequency and drug-name normalisers used by the grader
  run.py                   N runs per case; writes runs.jsonl, summary.md, failures.md; can rerun provider errors
  regrade.py               rescore an existing results directory with the current grader, keeping judge verdicts
  cases/                   18 case files with scripts or personas and expected outcomes
  test_sound_alike.py      target test for the sound-alike matcher and lookup tool
  audio/                   reusable speech set: utterances.yaml x voices.yaml -> clips + manifest; STT scorer and reports
  results/                 committed results: full-v1 … full-v6 (final), each with its prompt/tool snapshot
recording/                 audio of a real call, with transcript
report/
  build_report.py          builds evaluation_report.pdf from the committed results
  build_notes.py           builds agent_notes.pdf (what was built, what to harden next)
  theme.py                 shared fonts, palette and layout for both PDFs
INDEX.md                   links to every deliverable
EVAL.md                    evaluation strategy, results, verdict (long form of the report)
NOTES.md                   known weaknesses and what to harden first (long form of the note)
```

## Run it

```bash
uv sync
cp .env.example .env            # add MOONSHOT_API_KEY (or ANTHROPIC_API_KEY with MODEL=anthropic/...)

# one scripted case, in-process, transcript printed
uv run python -m evals.simulate --script evals/cases/happy_two_meds.yaml

# live text chat through the real server path
PORT=8000 uv run python main.py
cartesia chat 8000

# evaluation
uv run python -m evals.judge --calibrate            # judge agreement with hand labels
uv run python -m evals.run --runs 10                 # all cases, with judge
uv run python -m evals.run --cases wrong_person --runs 3 --no-judge
uv run python -m evals.regrade evals/results/full-v4  # rescore with the current grader, judge verdicts kept

# audio set (needs CARTESIA_API_KEY): build once, transcribe and score, rerun on a new STT model
uv run python -m evals.audio.build_set
uv run python -m evals.audio.stt_eval
uv run python -m evals.audio.stt_eval --model <newer-stt-model>

# deploy
cartesia deploy --agent-id <id>
cartesia env set --agent-id <id> --from .env
```

Model defaults to `moonshot/kimi-k2.6` with thinking disabled (see `provider_extras` in `intake/config.py` for why). Override with `MODEL=`. The judge uses `moonshot/kimi-k3`; override with `JUDGE_MODEL=`. The voice is chosen in the Cartesia agent console.
