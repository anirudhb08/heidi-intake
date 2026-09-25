"""record_intake: save the structured summary for the clinician.

This is the tool whose arguments the evaluation grades field by field, so the
schema is the contract. Two safety rules are enforced here in code:

  * refuse to save unless the session is verified (the identity gate)
  * a second call after a save is a no-op returning the same id

Blank doses and frequencies are allowed (the patient did not know) but are
listed under `unconfirmed_items` so the clinician sees exactly what to ask.
`intake_complete=false` marks a partial record taken when the patient ended
the call early; the alternative was losing everything they had said.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from line.llm_agent import loopback_tool

from intake.session import CallSession
from intake.tools.schema import Allergy, Medication


class RecordTool:
    def __init__(self, session: CallSession):
        self.session = session

    @loopback_tool
    async def record_intake(
        self,
        ctx,
        reason_for_visit: Annotated[str, "The main reason for the visit, in the patient's words"],
        medications: Annotated[list[Medication], "Every current medication the patient named, with dose and frequency as stated. Use an empty string for a dose or frequency the patient did not know."],
        allergies: Annotated[list[Allergy], "Medication or other allergies the patient named. Empty list if none."],
        relevant_history: Annotated[list[str], "Conditions, surgeries or other history the patient mentioned. Empty list if none."],
        patient_questions: Annotated[list[str], "Clinical questions the patient asked that must go to the clinician. Empty list if none."],
        intake_complete: Annotated[bool, "True if the patient confirmed the full readback. False if the patient ended the call early and this is a partial record."] = True,
    ) -> dict:
        """Save the intake summary for the clinician. Call this after the patient has
        confirmed the readback, or immediately with intake_complete=false if the patient
        ends the call early, so nothing collected is lost."""
        current_session = self.session

        # --- gate: enforced here, not in the prompt
        if not current_session.verified:
            current_session.log("tool", tool="record_intake", result="rejected_unverified")
            return {"saved": False, "error": "The patient has not confirmed their identity. Do not retry. End the call politely."}
        if current_session.recorded_intake is not None:
            return {"saved": True, "intake_id": current_session.recorded_intake["intake_id"], "note": "Already saved."}

        # --- normalise the medication list; blanks become unconfirmed items
        unconfirmed: list[str] = []
        clean_meds: list[dict] = []
        for m in medications:
            name = (m.get("name") or "").strip()
            if not name:
                continue
            dose = (m.get("dose") or "").strip()
            freq = (m.get("frequency") or "").strip()
            if not dose:
                unconfirmed.append(f"{name}: dose not known")
            if not freq:
                unconfirmed.append(f"{name}: frequency not known")
            clean_meds.append({
                "name": name, "dose": dose, "frequency": freq,
                "as_described": (m.get("as_described") or "").strip(),
            })

        record = {
            "intake_id": f"intake_{uuid.uuid4().hex[:8]}",
            "call_id": current_session.call_id,
            "patient_id": current_session.verified_patient["patient_id"],
            "appointment_date": current_session.verified_patient["appointment"]["date"],
            "reason_for_visit": reason_for_visit.strip(),
            "medications": clean_meds,
            "allergies": [
                {"substance": a.get("substance", "").strip(), "reaction": a.get("reaction", "").strip()}
                for a in allergies if a.get("substance", "").strip()
            ],
            "relevant_history": [h.strip() for h in relevant_history if h.strip()],
            "patient_questions": [q.strip() for q in patient_questions if q.strip()],
            "unconfirmed_items": unconfirmed,
            "intake_complete": bool(intake_complete),
            "escalated": current_session.escalated,
            "escalation": current_session.escalation,
        }
        current_session.recorded_intake = record
        path = current_session.write_intake(record)
        current_session.log("tool", tool="record_intake", args=record, result="saved", path=str(path))
        return {"saved": True, "intake_id": record["intake_id"], "unconfirmed_items": unconfirmed}
