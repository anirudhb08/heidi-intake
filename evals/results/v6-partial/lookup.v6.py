"""lookup_medication: normalise a spoken drug name and flag sound-alikes.

Called once per medication before the agent reads it back. Four outcomes:

  exact, no concern        -> read back and move on
  exact, sound-alike group -> ask the patient ONCE to spell it or say what it is
                              for, then record what they confirm
  ambiguous                -> the spoken name is close to more than one drug, or a
                              fuzzy hit whose sound-alike group came along. Never
                              resolved to one drug (the audio set showed hydralazine
                              heard as "Hydrolyzine" resolving to hydroxyzine). The
                              agent asks which, using what each is for, and otherwise
                              records the name as heard with the candidates
  not matched              -> do NOT ask for spelling (a real call showed the
                              second attempt comes back just as garbled);
                              ask what it is for and who gave it, record the
                              name as heard plus that description

The tool never says whether a medication is appropriate; its instruction
strings say so explicitly because the model reads them as prompt.
"""

from __future__ import annotations

from typing import Annotated

from line.llm_agent import loopback_tool

from intake.session import CallSession
from intake.tools.formulary import Formulary


class LookupTool:
    def __init__(self, session: CallSession, formulary: Formulary):
        self.session = session
        self.formulary = formulary

    @loopback_tool
    async def lookup_medication(
        self,
        ctx,
        spoken_name: Annotated[str, "The medication name as the patient said it"],
    ) -> dict:
        """Check a medication name the patient said against the clinic's medication list.
        Call this once for each medication the patient names, before reading it back.
        Returns the recognised name, or matched=false if it is not on the list, plus any
        sound-alike medications it could be confused with. Never use this to judge whether
        a medication is appropriate."""
        candidates, fuzzy = self.formulary.match(spoken_name)
        # sound-alike groups may list brand names; compare drugs, not spellings
        candidates = {self.formulary.canon(c) for c in candidates}

        if not candidates:
            result = {
                "matched": False,
                "instruction": (
                    "Not on the clinic list. Do not ask the patient to spell it. Ask once what it is for and "
                    "who gave it to them, then record the name exactly as they said it with that description in "
                    "as_described. If it is a cream, ointment, gel, drops, patch, spray or inhaler, do not ask "
                    "for a dose or how often; record what they volunteer. Do not suggest a different medication."
                ),
            }
        elif len(candidates) == 1 and not fuzzy:
            canon = next(iter(candidates))
            sound_alike = [self.formulary.canon(x) for x in self.formulary.sound_alikes([canon])]
            confirm = bool(sound_alike)
            result = {
                "matched": True,
                "recognised_name": canon,
                "sound_alike": sound_alike,
                "confirm_recommended": confirm,
            }
            if confirm:
                result["instruction"] = (
                    f"'{spoken_name}' can be confused with {', '.join(sound_alike)}. "
                    "Read the name back and ask the patient once to spell it or say what they take it for. "
                    "Record what the patient confirms. If they move on, record it as said. "
                    "Do not comment on the medication itself."
                )
        else:
            # Ambiguous: a garbled name close to more than one drug, or a fuzzy hit
            # whose sound-alike group came along. Never resolve this to one drug:
            # the audio evaluation showed "Hydrolyzine" resolving to hydroxyzine
            # when the patient meant hydralazine.
            described = [f"{c} ({self.formulary.entries.get(c, {}).get('class', 'medication')})" for c in sorted(candidates)]
            result = {
                "matched": False,
                "candidates": sorted(candidates),
                "instruction": (
                    f"'{spoken_name}' could be more than one medication: {'; '.join(described)}. "
                    "Read the name back exactly as the patient said it and ask which one it is, using what "
                    "each is for, for example the one for blood pressure or the one for itching. Do not ask them "
                    "to spell it. If they settle it, record that name. If they cannot, record the name exactly as "
                    "they said it and put the candidates in as_described. Never choose one yourself."
                ),
            }

        self.session.log("tool", tool="lookup_medication", args={"spoken_name": spoken_name}, result=result)
        return result
