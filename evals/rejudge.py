"""Re-run only the LLM judge over an existing results directory, keeping every
deterministic grade, and report how the verdicts changed.

    uv run python -m evals.rejudge evals/results/full-v5
    uv run python -m evals.rejudge evals/results/full-v6 --only-unjudged   # fill in runs the judge could not score

Used after a judge fix (for example: an unparseable judge reply used to count as
a pass; it is now "unjudged"). The previous verdicts are kept in
runs.before-rejudge.jsonl so the change is auditable.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.run import JUDGE_DIM, judge, write_results  # noqa: E402


async def main(out_dir: Path, concurrency: int, only_unjudged: bool = False) -> None:
    source = out_dir / "runs.jsonl"
    (out_dir / "runs.before-rejudge.jsonl").write_text(source.read_text())
    results = [json.loads(line) for line in source.read_text().splitlines()]
    gate = asyncio.Semaphore(concurrency)
    targets = [r for r in results if not only_unjudged or r["grade"].get(JUDGE_DIM, {}).get("pass") is None]

    async def rejudge(r: dict) -> None:
        async with gate:
            r["grade"][JUDGE_DIM] = await judge(r)
            deterministic = all(g["pass"] for k, g in r["grade"].items() if isinstance(g, dict) and k != JUDGE_DIM)
            r["grade"]["overall"] = deterministic and r["grade"][JUDGE_DIM]["pass"] is True
            safety = all(r["grade"][d]["pass"] for d in ("E5_verification_gate", "E4_escalation", "E3_safety_screen", "E2_fabrication"))
            r["grade"]["safety_ok"] = safety and r["grade"][JUDGE_DIM]["pass"] is not False

    before = {(r["case"], r["run_index"]): r["grade"][JUDGE_DIM]["pass"] for r in results}
    await asyncio.gather(*(rejudge(r) for r in targets))
    after = {(r["case"], r["run_index"]): r["grade"][JUDGE_DIM]["pass"] for r in results}
    changed = [(k, before[k], after[k]) for k in before if before[k] != after[k]]
    print(f"{out_dir.name}: {len(targets)} runs re-judged; verdicts changed: {len(changed)}")
    for key, was, now in changed:
        print(f"   {key[0]} run {key[1]}: {was} -> {now}")
    write_results(results, out_dir, model=None, use_judge=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    asyncio.run(main(Path(args[0]), int(args[1]) if len(args) > 1 else 3, only_unjudged="--only-unjudged" in sys.argv))
