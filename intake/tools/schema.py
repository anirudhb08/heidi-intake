"""The record schema the model fills in.

These TypedDicts double as the JSON schema the model sees: Line converts them
to strict object schemas, so every field is required and the model must send
"" for anything the patient did not know. The record tool turns those blanks
into `unconfirmed_items` so the clinician sees what is missing.
"""

from __future__ import annotations

from typing import TypedDict


class Medication(TypedDict):
    name: str  # exactly as the patient said it, never "corrected"
    dose: str  # e.g. "20 mg"; "" if the patient does not know
    frequency: str  # e.g. "once daily"; "" if the patient does not know
    as_described: str  # patient's description when the name was not recognised, e.g. "a cream for a burn"; else ""


class Allergy(TypedDict):
    substance: str
    reaction: str  # "" if not stated
