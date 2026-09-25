"""Target behaviour for the sound-alike fix. Run until green:

    uv run python -m evals.test_sound_alike

WHAT IS WRONG TODAY
  Formulary.match("hydrolyzine") returns ("hydroxyzine", fuzzy=True). Both hydroxyzine (0.91)
  and hydralazine (0.82) clear the 0.8 cutoff; the runner-up is discarded. lookup_medication
  then tells the agent it heard hydroxyzine, the agent reads that back, and a patient who
  cannot hear the difference says yes. The audio set produced exactly this (Indian voice,
  hydralazine -> "Hydrolyzine" -> hydroxyzine). A wrong drug in the record is the worst
  outcome the tool can produce.

WHERE THE CHANGE GOES
  1. intake/tools/formulary.py   Formulary.match must surface every candidate that clears
     the cutoff (and the sound-alike group of a fuzzy winner), not just the best one.
     Suggested shape: match(spoken) -> MatchResult(exact: str | None, candidates: list[str], fuzzy: bool)
  2. intake/tools/lookup.py      a new outcome, "ambiguous": matched=false, candidates listed with
     what each is for (the formulary has a `class` per drug), and an instruction that says:
     read it back as heard, ask which one using what each is for, and if the patient does not
     settle it, record the name as heard with both candidates in as_described. Never pick one.
  3. intake/prompt.py            the MEDICATIONS rule for the ambiguous case (one sentence).
  4. evals/audio/stt_eval.py     agent_recovery() calls Formulary.match; update it for the new
     return shape so the audio report's "WRONG_DRUG" column reflects the fix.

ACCEPTANCE
  - this file passes
  - `uv run python -m evals.run --cases sound_alike_garbled sound_alike_drug --runs 10`
    both 10/10 (the existing Klonopin case must not regress: a clean exact alias hit
    is still a confident match)
  - `uv run python -m evals.audio.stt_eval` reports "mapped to a wrong drug 0"
"""

from __future__ import annotations

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intake.session import CallSession  # noqa: E402
from intake.tools.formulary import Formulary  # noqa: E402
from intake.tools.lookup import LookupTool  # noqa: E402

f = Formulary()
failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def candidates(spoken: str) -> set[str]:
    """Adapter so the assertions below survive whatever shape you give match()."""
    r = f.match(spoken)
    if isinstance(r, tuple):  # (canon | None, fuzzy) or (set_of_canons, fuzzy)
        first = r[0]
        if isinstance(first, (set, list, tuple)):
            return set(first)
        return {first} if first else set()
    return set(getattr(r, "candidates", [])) | ({r.exact} if getattr(r, "exact", None) else set())


# --- formulary level -------------------------------------------------------
c = candidates("hydrolyzine")
check("garble within cutoff of two drugs surfaces both", c >= {"hydroxyzine", "hydralazine"}, f"got {c}")
c = candidates("hydrolazine")
check("same for the mirror garble", c >= {"hydroxyzine", "hydralazine"}, f"got {c}")
c = candidates("metaprolol")
check("fuzzy hit whose winner has a sound-alike group surfaces the group", c >= {"metoprolol", "misoprostol"}, f"got {c}")
c = candidates("lysinopril")
check("fuzzy hit with no sound-alike stays a single candidate", c == {"lisinopril"}, f"got {c}")
c = candidates("klonopin")
check("exact alias hit is still a confident single match", c == {"clonazepam"}, f"got {c}")
c = candidates("turmeric")
check("unknown name has no candidates", c == set(), f"got {c}")


# --- tool level ------------------------------------------------------------
async def lookup(spoken: str) -> dict:
    s = CallSession("test", log_path=pathlib.Path("/tmp/sound_alike_test.jsonl"))
    return await LookupTool(s, f).lookup_medication.func(None, spoken_name=spoken)

r = asyncio.run(lookup("Hydrolyzine"))
check("ambiguous lookup does not claim a match", r.get("matched") is False, f"got matched={r.get('matched')}")
check("ambiguous lookup lists both candidates", set(r.get("candidates", [])) >= {"hydroxyzine", "hydralazine"}, f"got {r.get('candidates')}")
check("ambiguous lookup says what each candidate is for", all(k in str(r).lower() for k in ("antihistamine", "vasodilator")), "instruction should use the formulary class")
check("ambiguous lookup never names one drug as recognised", "recognised_name" not in r, f"got recognised_name={r.get('recognised_name')}")
r = asyncio.run(lookup("Klonopin"))
check("clean sound-alike hit still asks to confirm, as before", r.get("matched") is True and r.get("confirm_recommended") is True)

print(f"\n{len(failures)} failing" if failures else "\nall green")
sys.exit(1 if failures else 0)
