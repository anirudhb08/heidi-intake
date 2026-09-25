"""A tiny demo formulary: 61 common medications with brand aliases, common
misspellings, and sound-alike groups.

This stands in for a real drug database. Its two jobs:
  1. map whatever the patient said ("Lipitor", "lisinapril") to a canonical
     generic name so the record is consistent;
  2. flag names that speech recognition confuses (Klonopin/clonidine,
     hydroxyzine/hydralazine) so the agent confirms before recording.

The same class is used by the evaluation normaliser so "Klonopin" in a
recorded intake matches "clonazepam" in a case's expected record.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PATH = ROOT / "data" / "medications.json"

#: difflib ratio below which a spoken name is treated as unknown rather than
#: fuzzy-matched. 0.8 catches one-letter slips without mapping "Sufra" to
#: something it is not.
FUZZY_CUTOFF = 0.8


def normalise_key(text: str) -> str:
    """Lookup key: lowercase, letters/digits/space/hyphen only."""
    return re.sub(r"[^a-z0-9 \-]", "", text.strip().lower())


class Formulary:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.entries: dict[str, dict] = json.loads(Path(path).read_text())["medications"]
        # alias (lowercase) -> canonical generic name, canonical names included
        self.alias: dict[str, str] = {}
        for canon, info in self.entries.items():
            self.alias[canon] = canon
            for a in info.get("aliases", []):
                self.alias[a.lower()] = canon

    def canon(self, name: str) -> str:
        """Canonical generic name for an exact alias match, else the key form
        of the input unchanged. Never fuzzy: used for comparisons in grading."""
        key = normalise_key(name)
        return self.alias.get(key, key)

    def match(self, spoken: str) -> tuple[set[str], bool]:
        """(candidate canonical names, was_fuzzy).

        An exact alias hit returns one name. A fuzzy hit returns every drug
        within FUZZY_CUTOFF plus the sound-alike group of each, so a garble
        like "hydrolyzine" yields {hydroxyzine, hydralazine} and the caller
        can ask rather than guess. No hit returns an empty set."""
        key = normalise_key(spoken)
        if key in self.alias:
            return {self.alias[key]}, False
        close = difflib.get_close_matches(key, list(self.alias), n=5, cutoff=FUZZY_CUTOFF)
        if close:
            sound_alikes = self.sound_alikes([self.alias[a] for a in close])
            return {self.alias[a] for a in close}.union(sound_alikes), True

        return set(), False

    def sound_alikes(self, canon: list[str]) -> list[str]:
        """Union of the sound-alike groups of the given canonical names."""
        sound_alike_values = []

        for entry in canon:
            sound_alike_values.extend(
                list(self.entries.get(entry, {}).get("sound_alike", []))
            )

        return sorted(set(sound_alike_values))
