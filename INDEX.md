# Heidi Health pre-visit intake agent: index

Cartesia FDE take-home. A patient-facing voice agent on Cartesia Line, and the evaluation that says whether it is safe enough to ship.

| What | Where |
|---|---|
| **Evaluation results** (4 pages: strategy, rule-based results, AI judge, voice layer, verdict) | [report/evaluation_report.pdf](report/evaluation_report.pdf) |
| **What was built and what to harden next** (2 pages, for an external reader) | [report/agent_notes.pdf](report/agent_notes.pdf) |
| **Recording of a real call** | [recording/call_recording.wav](recording/call_recording.wav) · [transcript](recording/call_recording.transcript.txt) |
| **Agent code** | [main.py](main.py) (Line entry point) · [intake/](intake/) · [prompt](intake/prompt.py) · [tools](intake/tools/) |
| **Evaluation code** | [evals/](evals/) · [simulate.py](evals/simulate.py) · [grade.py](evals/grade.py) · [judge.py](evals/judge.py) · [run.py](evals/run.py) · [cases/](evals/cases/) · [audio/](evals/audio/) |

Long-form markdown behind the two PDFs: [EVAL.md](EVAL.md) (strategy and results in full) and [NOTES.md](NOTES.md) (known weaknesses, with a longer version in [evals/results/NOTES.long.md](evals/results/NOTES.long.md)).

How to run the agent, the harness and the audio set: [README.md](README.md). The PDFs are rebuilt from the committed results with `uv run python report/build_report.py` and `uv run python report/build_notes.py`.
