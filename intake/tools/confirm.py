"""confirm_patient: the identity gate for an outbound call.

The clinic dialled the number on file, so the patient is already known. The
agent opens with "Am I speaking with <first name>?" and this tool records the
answer. A yes opens the gate; anything else closes the call.

Deliberate shortcut for this exercise: a yes is trusted. No date of birth, no
second identifier. Possession of the phone on file plus a claimed name is a
weaker bar than most clinics use for sharing appointment details, and the
write-up lists it as such. The gate itself is still enforced in code:
`record_intake` refuses to save until this tool has returned matched=true.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from line.llm_agent import loopback_tool

from intake.session import CallSession


class ConfirmTool:
    def __init__(self, session: CallSession):
        self.session = session

    @loopback_tool
    async def confirm_patient(
        self,
        ctx,
        answered_by: Annotated[Literal["patient", "someone_else", "unclear"], "'patient' if the person says they are the patient you asked for. 'someone_else' if they say they are not, or that the patient is unavailable, or that it is the wrong number. 'unclear' if you could not tell."],
    ) -> dict:
        """Record who answered the call. Call this as soon as the person says whether they
        are the patient. Until it returns matched=true, do not mention the appointment or ask
        any intake question."""
        s = self.session
        s.log("tool", tool="confirm_patient", args={"answered_by": answered_by})

        if s.expected_patient is None:
            return {"matched": False, "instruction": "This number is not on file. Apologise for the wrong number and end the call."}
        if answered_by == "patient":
            s.verified_patient = s.expected_patient
            return {"matched": True, **_summary(s.expected_patient)}
        if answered_by == "unclear":
            return {"matched": False, "instruction": f"Ask once more whether you are speaking with {s.expected_patient['first_name']}."}
        return {
            "matched": False,
            "instruction": "Do not say what the call is about beyond a pre-visit call from the clinic. "
                           "Say the clinic will try again another time, say goodbye, and call end_call in the same turn.",
        }


def _summary(p: dict) -> dict:
    """What the model may now say: first name and the appointment. The full
    record (last name, phone, date of birth) is never returned to the model."""
    appt = p["appointment"]
    return {
        "patient_id": p["patient_id"],
        "first_name": p["first_name"],
        "appointment_day": date.fromisoformat(appt["date"]).strftime("%A"),
        "appointment_date": appt["date"],
        "appointment_time": appt["time"],
        "clinician": appt["clinician"],
    }
