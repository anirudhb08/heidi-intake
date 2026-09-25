"""Intake tools. All state lives on the CallSession so the safety gates are
enforced here, not in the prompt.

Every tool takes ``ctx`` first (Line requirement) and returns a plain dict,
which the SDK JSON-encodes and hands back to the model.
"""

from __future__ import annotations

import difflib
import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from line.llm_agent import loopback_tool

from session import CallSession

ROOT = Path(__file__).resolve().parent
PATIENTS_PATH = ROOT / "data" / "patients.json"
MEDICATIONS_PATH = ROOT / "data" / "medications.json"

MAX_VERIFICATION_ATTEMPTS = 2

_DOB_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%B %d %Y", "%B %d, %Y", "%d %B %Y", "%b %d %Y", "%b %d, %Y")


def _norm_name(s: str) -> list[str]:
    return [t for t in re.sub(r"[^a-z ]", " ", s.lower()).split() if t]


def _parse_dob(s: str) -> date | None:
    s = s.strip().replace("st ", " ").replace("nd ", " ").replace("rd ", " ").replace("th ", " ")
    for fmt in _DOB_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


class Medication(TypedDict):
    name: str
    dose: str  # e.g. "20 mg"; empty string if the patient does not know
    frequency: str  # e.g. "once daily"; empty string if the patient does not know


class Allergy(TypedDict):
    substance: str
    reaction: str  # empty string if not stated


class IntakeTools:
    def __init__(self, session: CallSession, patients_path: Path = PATIENTS_PATH,
                 medications_path: Path = MEDICATIONS_PATH):
        self.session = session
        self.patients: list[dict] = json.loads(Path(patients_path).read_text())
        self.formulary: dict[str, dict] = json.loads(Path(medications_path).read_text())["medications"]
        # alias -> canonical
        self._alias_index: dict[str, str] = {}
        for canon, info in self.formulary.items():
            self._alias_index[canon] = canon
            for a in info.get("aliases", []):
                self._alias_index[a.lower()] = canon

    # ------------------------------------------------------------------ lookup

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
        s = self.session
        raw = spoken_name.strip().lower()
        key = re.sub(r"[^a-z0-9 \-]", "", raw)
        canon = self._alias_index.get(key)
        fuzzy = None
        if canon is None:
            close = difflib.get_close_matches(key, list(self._alias_index.keys()), n=1, cutoff=0.8)
            if close:
                fuzzy = close[0]
                canon = self._alias_index[fuzzy]

        if canon is None:
            result = {
                "matched": False,
                "heard_as": spoken_name,
                "instruction": "Not on the clinic list. Ask the patient to spell it, record it exactly as they say it, "
                               "and do not suggest a different medication.",
            }
        else:
            info = self.formulary[canon]
            sound_alike = info.get("sound_alike", [])
            result = {
                "matched": True,
                "heard_as": spoken_name,
                "recognised_name": canon,
                "fuzzy_match": fuzzy is not None,
                "sound_alike": sound_alike,
                "confirm_recommended": bool(sound_alike) or fuzzy is not None,
            }
            if result["confirm_recommended"]:
                result["instruction"] = (
                    f"'{spoken_name}' can be confused with {', '.join(sound_alike) or 'a similar name'}. "
                    "Read the name back and ask the patient to spell it or say what they take it for. "
                    "Record what the patient confirms. Do not comment on the medication itself."
                )
        s.log("tool", tool="lookup_medication", args={"spoken_name": spoken_name}, result=result)
        return result

    # ------------------------------------------------------------------ verify

    @loopback_tool
    async def verify_patient(
        self,
        ctx,
        full_name: Annotated[str, "The patient's full name as they said it"],
        date_of_birth: Annotated[str, "Date of birth in YYYY-MM-DD form"],
    ) -> dict:
        """Check the caller's name and date of birth against the clinic record.
        Call this before sharing any appointment detail or asking any intake question.
        Returns matched=true with the patient's first name and appointment details,
        or matched=false with the number of attempts remaining."""
        s = self.session
        if s.verified:
            return {"matched": True, "note": "Patient already verified.", **self._patient_summary(s.verified_patient)}

        s.verification_attempts += 1
        dob = _parse_dob(date_of_birth)
        tokens = set(_norm_name(full_name))
        match = None
        for p in self.patients:
            p_tokens = {p["first_name"].lower(), p["last_name"].lower()}
            if dob and date.fromisoformat(p["date_of_birth"]) == dob and p_tokens <= tokens:
                match = p
                break

        if match:
            s.verified_patient = match
            s.log("tool", tool="verify_patient", args={"full_name": full_name, "date_of_birth": date_of_birth}, result="matched")
            return {"matched": True, **self._patient_summary(match)}

        remaining = MAX_VERIFICATION_ATTEMPTS - s.verification_attempts
        s.log("tool", tool="verify_patient", args={"full_name": full_name, "date_of_birth": date_of_birth},
              result="no_match", attempts_remaining=remaining)
        if remaining <= 0:
            return {
                "matched": False,
                "attempts_remaining": 0,
                "instruction": "Verification failed twice. Apologise, say the clinic will follow up by phone, "
                               "do not share or collect anything, and end the call.",
            }
        return {"matched": False, "attempts_remaining": remaining,
                "instruction": "Ask the caller to repeat their full name and date of birth once more."}

    @staticmethod
    def _patient_summary(p: dict) -> dict:
        appt = p["appointment"]
        appt_date = date.fromisoformat(appt["date"])
        return {
            "patient_id": p["patient_id"],
            "first_name": p["first_name"],
            "appointment_day": appt_date.strftime("%A"),
            "appointment_date": appt["date"],
            "appointment_time": appt["time"],
            "clinician": appt["clinician"],
        }

    # ------------------------------------------------------------------ record

    @loopback_tool
    async def record_intake(
        self,
        ctx,
        reason_for_visit: Annotated[str, "The main reason for the visit, in the patient's words"],
        medications: Annotated[list[Medication], "Every current medication the patient named, with dose and frequency as stated. Use an empty string for a dose or frequency the patient did not know."],
        allergies: Annotated[list[Allergy], "Medication or other allergies the patient named. Empty list if none."],
        relevant_history: Annotated[list[str], "Conditions, surgeries or other history the patient mentioned. Empty list if none."],
        patient_questions: Annotated[list[str], "Clinical questions the patient asked that must go to the clinician. Empty list if none."],
    ) -> dict:
        """Save the completed intake summary for the clinician. Call this only after
        the patient has confirmed the readback of everything collected."""
        s = self.session
        if not s.verified:
            s.log("tool", tool="record_intake", result="rejected_unverified")
            return {"saved": False, "error": "Patient is not verified. Do not retry. End the call politely."}
        if s.recorded_intake is not None:
            return {"saved": True, "intake_id": s.recorded_intake["intake_id"], "note": "Already saved."}

        unconfirmed = []
        clean_meds = []
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
            clean_meds.append({"name": name, "dose": dose, "frequency": freq})

        record = {
            "intake_id": f"intake_{uuid.uuid4().hex[:8]}",
            "call_id": s.call_id,
            "patient_id": s.verified_patient["patient_id"],
            "appointment_date": s.verified_patient["appointment"]["date"],
            "reason_for_visit": reason_for_visit.strip(),
            "medications": clean_meds,
            "allergies": [{"substance": a.get("substance", "").strip(), "reaction": a.get("reaction", "").strip()}
                          for a in allergies if a.get("substance", "").strip()],
            "relevant_history": [h.strip() for h in relevant_history if h.strip()],
            "patient_questions": [q.strip() for q in patient_questions if q.strip()],
            "unconfirmed_items": unconfirmed,
            "escalated": s.escalated,
            "escalation": s.escalation,
            "verification_passed": True,
        }
        s.recorded_intake = record
        path = s.write_intake(record)
        s.log("tool", tool="record_intake", args=record, result="saved", path=str(path))
        return {"saved": True, "intake_id": record["intake_id"], "unconfirmed_items": unconfirmed}

    # ---------------------------------------------------------------- escalate

    @loopback_tool
    async def escalate_to_human(
        self,
        ctx,
        reason: Annotated[str, "Short description of why a person needs to call back"],
        urgency: Annotated[Literal["now", "today"], "'now' if the symptom is happening right now, otherwise 'today'"],
        symptom_quote: Annotated[str, "The patient's own words that triggered the escalation"],
    ) -> dict:
        """Flag the call for an urgent nurse callback. Use immediately for any red-flag
        symptom (chest pain, trouble breathing, stroke signs, severe bleeding, allergic
        reaction, thoughts of self-harm) or if the patient asks for a person. After
        calling this, do not ask further intake questions."""
        s = self.session
        s.escalated = True
        s.escalation = {"reason": reason, "urgency": urgency, "symptom_quote": symptom_quote}
        s.log("tool", tool="escalate_to_human", args=s.escalation, result="callback_scheduled")
        return {
            "callback_scheduled": True,
            "instruction": ("Tell the patient a nurse will call them back shortly on the number on file. "
                            + ("If it is happening right now, tell them to call emergency services. " if urgency == "now" else "")
                            + "Do not ask any more intake questions. Say goodbye and end the call."),
        }

    def all(self) -> list:
        return [self.verify_patient, self.lookup_medication, self.record_intake, self.escalate_to_human]
