"""Re-score an existing results directory with the current grader, keeping judge verdicts.

    uv run python -m evals.regrade evals/results/full-v5

Use this after fixing a grader bug, so committed results reflect the fixed
grader without rerunning conversations or the judge.

Only valid for result sets produced under the CURRENT case files and tool
names. Older sets (before the identity flow changed the confirm tool's name,
or whose cases have since been renamed) would be graded against expectations
they were never run with, so the script refuses them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.grade import grade  # noqa: E402
from evals.run import JUDGE_DIM, load_cases, write_results  # noqa: E402

CURRENT_IDENTITY_TOOL = "confirm_patient"


def main(out_dir: Path) -> None:
    source = out_dir / "runs.jsonl"
    results = [json.loads(line) for line in source.read_text().splitlines()]
    cases = {c["id"]: c for c in load_cases(None)}

    missing = sorted({r["case"] for r in results} - set(cases))
    if missing:
        sys.exit(f"refusing: cases {missing} no longer exist; this result set predates the current case files")
    tools_seen = {c["name"] for r in results for t in r["transcript"] for c in t.get("tool_calls", [])}
    if tools_seen and CURRENT_IDENTITY_TOOL not in tools_seen and "verify_patient" in tools_seen:
        sys.exit("refusing: this result set used verify_patient; the current cases expect confirm_patient")

    for r in results:
        previous_judge = r["grade"].get(JUDGE_DIM)
        r["grade"] = grade(r, cases[r["case"]])
        if previous_judge is not None:
            r["grade"][JUDGE_DIM] = previous_judge
            r["grade"]["overall"] = r["grade"]["overall"] and previous_judge["pass"] is True
            r["grade"]["safety_ok"] = r["grade"]["safety_ok"] and previous_judge["pass"] is not False
    write_results(results, out_dir, model=None, use_judge=any(JUDGE_DIM in r["grade"] for r in results))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
