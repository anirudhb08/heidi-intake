"""The patient fixture and a lookup by phone number.

Three fake records. `by_phone` is what an outbound call uses to know who it is
calling before the first word; `by_id` is what the evaluation harness uses to
stage a call for a given case.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATIENTS_PATH = ROOT / "data" / "patients.json"

_PATIENTS: list[dict] = json.loads(PATIENTS_PATH.read_text())


def _digits(number: str) -> str:
    return re.sub(r"\D", "", number or "")


def by_phone(number: str) -> dict | None:
    """Match on digits only, so "+1 555 010 0001" equals "15550100001"."""
    d = _digits(number)
    if not d:
        return None
    return next((p for p in _PATIENTS if _digits(p["phone_on_file"]) == d), None)


def by_id(patient_id: str) -> dict | None:
    return next((p for p in _PATIENTS if p["patient_id"] == patient_id), None)
