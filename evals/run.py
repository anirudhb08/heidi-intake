"""Run every case N times, grade each run, and write results.

    uv run python -m evals.run --cases happy_two_meds wrong_person --runs 3 --no-judge
    uv run python -m evals.run --runs 10                       # all cases, with the judge
    uv run python -m evals.run --rerun-errors evals/results/full-v1   # redo only provider-error runs

Outputs, in evals/results/<timestamp>/ unless --out is given:
    runs.jsonl           one line per run: transcript, tool calls, intake record, grades
    runs.partial.jsonl   the same, appended as each run finishes, so a stalled run still has data
    summary.md           pass counts per case per dimension, and a headline
    failures.md          every failed check with its evidence and the transcript

A judge that could not return a verdict is recorded as "unjudged": not a pass,
not a safety failure, and reported separately.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import TextIO

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.grade import CHECKS, SAFETY_DIMS, grade  # noqa: E402
from evals.judge import judge_run  # noqa: E402
from evals.simulate import run_persona, run_script  # noqa: E402

CASES_DIR = ROOT / "evals" / "cases"
RESULTS_DIR = ROOT / "evals" / "results"
JUDGE_DIM = "E3_judge"


# ------------------------------------------------------------------ running

def load_cases(ids: list[str] | None) -> list[dict]:
    cases = [yaml.safe_load(p.read_text()) for p in sorted(CASES_DIR.glob("*.yaml"))]
    return [c for c in cases if not ids or c["id"] in ids]


async def simulate(case: dict, model: str | None):
    kwargs = {"model": model, "patient_id": case.get("patient")}
    if case.get("type") == "persona":
        return await run_persona(case["persona"], **kwargs)
    return await run_script(case["script"], **kwargs)


async def judge(run: dict) -> dict:
    """The judge's verdict as a grade entry. pass=None means no verdict could be obtained."""
    try:
        result = await judge_run(run)
    except Exception as e:
        return {"pass": None, "evidence": f"unjudged: {type(e).__name__}: {str(e)[:120]}", "violations": []}
    return {"pass": result["pass"], "evidence": result["evidence"],
            "violations": result.get("violations", []), "overruled": result.get("flagged_but_overruled", [])}


async def run_one(case: dict, index: int, gate: asyncio.Semaphore, model: str | None, use_judge: bool) -> dict:
    async with gate:
        started = time.perf_counter()
        result = (await simulate(case, model)).to_dict()
        result.update(case=case["id"], run_index=index, seconds=round(time.perf_counter() - started, 1))
        result["grade"] = grade(result, case)
        if use_judge:
            grades = result["grade"]
            grades[JUDGE_DIM] = await judge(result)
            grades["overall"] = grades["overall"] and grades[JUDGE_DIM]["pass"] is True
            grades["safety_ok"] = grades["safety_ok"] and grades[JUDGE_DIM]["pass"] is not False
        return result


def status_of(result: dict) -> str:
    grades = result["grade"]
    return "PASS" if grades["overall"] else ("SAFETY-FAIL" if not grades["safety_ok"] else "fail")


def failed_dimensions(result: dict) -> list[str]:
    return [name for name, g in result["grade"].items() if isinstance(g, dict) and g["pass"] is not True]


def progress_line(done: int, total: int, result: dict) -> str:
    error = f"  ERROR: {result['error'][:90]}" if result.get("error") else ""
    return (f"  [{done}/{total}] {result['case']:28s} run {result['run_index']:2d}  {status_of(result):11s} "
            f"{result['seconds']:6.1f}s  {' '.join(failed_dimensions(result))}{error}")


async def main(case_ids, runs: int, concurrency: int, model: str | None, out_dir: Path, use_judge: bool) -> None:
    cases = load_cases(case_ids)
    if not cases:
        sys.exit("no cases matched")
    gate = asyncio.Semaphore(concurrency)
    jobs = [run_one(case, i, gate, model, use_judge) for case in cases for i in range(runs)]
    print(f"{len(cases)} cases x {runs} runs = {len(jobs)} conversations, concurrency {concurrency}", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with (out_dir / "runs.partial.jsonl").open("w") as partial:
        for job in asyncio.as_completed(jobs):
            result = await job
            results.append(result)
            partial.write(json.dumps(result) + "\n")
            partial.flush()
            print(progress_line(len(results), len(jobs), result), flush=True)
    write_results(results, out_dir, model, use_judge)


async def rerun_errors(out_dir: Path, concurrency: int, model: str | None, use_judge: bool) -> None:
    """Replace runs that died on a provider error with fresh ones. The original
    file is kept as runs.before-rerun.jsonl so the infrastructure failure rate stays visible."""
    source = out_dir / "runs.jsonl"
    (out_dir / "runs.before-rerun.jsonl").write_text(source.read_text())
    cases = {c["id"]: c for c in load_cases(None)}
    results = [json.loads(line) for line in source.read_text().splitlines()]
    to_redo = [i for i, r in enumerate(results) if r.get("error")]
    print(f"{len(to_redo)} of {len(results)} runs had provider errors; re-running at concurrency {concurrency}")
    gate = asyncio.Semaphore(concurrency)

    async def redo(position: int) -> None:
        old = results[position]
        new = await run_one(cases[old["case"]], old["run_index"], gate, model, use_judge)
        new["rerun_of_error"] = old["error"]
        results[position] = new
        print(progress_line(position + 1, len(to_redo), new), flush=True)

    await asyncio.gather(*(redo(i) for i in to_redo))
    write_results(results, out_dir, model, use_judge)


# ------------------------------------------------------------------ reporting

def dimension_names(use_judge: bool) -> list[str]:
    return list(CHECKS) + ([JUDGE_DIM] if use_judge else [])


def summary_markdown(results: list[dict], model: str | None, use_judge: bool) -> str:
    dims = dimension_names(use_judge)
    safety_dims = list(SAFETY_DIMS) + ([JUDGE_DIM] if use_judge else [])
    by_case: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_case[r["case"]].append(r)

    def cell(runs: list[dict], dim: str) -> tuple[int, str]:
        passed = sum(1 for r in runs if r["grade"][dim]["pass"] is True)
        unjudged = sum(1 for r in runs if r["grade"][dim]["pass"] is None)
        text = f"{passed}/{len(runs)}" + ("" if passed == len(runs) else " ✗") + (f" ({unjudged} unjudged)" if unjudged else "")
        return passed, text

    lines = ["# Evaluation results", "",
             f"Model: `{model or 'default (see main.py)'}`  ·  {len(results)} runs  ·  {datetime.now():%Y-%m-%d %H:%M}", "",
             "Cells are runs passed / runs. Safety dimensions (E2, E3 screen + judge, E4, E5) must be N/N to ship.", "",
             "| case | runs | " + " | ".join(dims) + " | overall |", "|---|---|" + "---|" * (len(dims) + 1)]
    totals = {dim: 0 for dim in dims}
    overall_passed = 0
    for case_id, runs in by_case.items():
        cells = []
        for dim in dims:
            passed, text = cell(runs, dim)
            totals[dim] += passed
            cells.append(text)
        case_passed = sum(1 for r in runs if r["grade"]["overall"])
        overall_passed += case_passed
        lines.append(f"| {case_id} | {len(runs)} | " + " | ".join(cells) + f" | {case_passed}/{len(runs)} |")
    lines.append(f"| **all** | {len(results)} | " + " | ".join(f"{totals[d]}/{len(results)}" for d in dims)
                 + f" | {overall_passed}/{len(results)} |")

    safety_failures = sum(1 for r in results if not r["grade"]["safety_ok"])
    unjudged = sum(1 for r in results if use_judge and r["grade"][JUDGE_DIM]["pass"] is None)
    worst_case, worst_runs = min(by_case.items(), key=lambda kv: sum(r["grade"]["overall"] for r in kv[1]) / len(kv[1]))
    seconds = sorted(r["seconds"] for r in results)
    lines += ["", "## Headline", "",
              f"- Safety-critical failures (any of {', '.join(safety_dims)}): **{safety_failures}** of {len(results)} runs",
              f"- Runs passing every check: **{overall_passed}/{len(results)}**"
              + (f" (plus {unjudged} runs the judge could not score)" if unjudged else ""),
              f"- Worst case: `{worst_case}` at {sum(r['grade']['overall'] for r in worst_runs)}/{len(worst_runs)}",
              f"- Wall time per conversation: min {seconds[0]}s, median {seconds[len(seconds) // 2]}s, max {seconds[-1]}s"]
    return "\n".join(lines) + "\n"


def failures_markdown(results: list[dict]) -> str:
    lines = ["# Failures", ""]
    for r in results:
        failed = [(name, r["grade"][name]) for name in failed_dimensions(r)]
        if not failed:
            continue
        lines += [f"## {r['case']} run {r['run_index']}"]
        lines += [f"- **{name}**: {g['evidence']}" for name, g in failed]
        lines += ["", "<details><summary>transcript</summary>", ""]
        for t in r["transcript"]:
            lines.append(f"- **{t['role']}**: {t['text']}")
            lines += [f"    - tool `{c['name']}` {json.dumps(c['args'])[:200]}" for c in t.get("tool_calls", [])]
        lines += ["", "</details>", ""]
    return "\n".join(lines) + "\n"


def write_results(results: list[dict], out_dir: Path, model: str | None, use_judge: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    results.sort(key=lambda r: (r["case"], r["run_index"]))
    (out_dir / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in results))
    summary = summary_markdown(results, model, use_judge)
    (out_dir / "summary.md").write_text(summary)
    (out_dir / "failures.md").write_text(failures_markdown(results))
    print(f"\nwrote {out_dir}/summary.md, failures.md, runs.jsonl")
    print(summary.split("\n", 6)[6])  # the table and headline, without the title lines


# ------------------------------------------------------------------ entry point

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="*")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--model")
    parser.add_argument("--out", help="results dir; default evals/results/<timestamp>")
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM safety judge")
    parser.add_argument("--rerun-errors", help="results dir: re-execute only runs whose error field is set")
    args = parser.parse_args()
    if args.rerun_errors:
        asyncio.run(rerun_errors(Path(args.rerun_errors), args.concurrency, args.model, not args.no_judge))
    else:
        out = Path(args.out) if args.out else RESULTS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
        asyncio.run(main(args.cases, args.runs, args.concurrency, args.model, out, not args.no_judge))
