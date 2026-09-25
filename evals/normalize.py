"""Normalizers so the grader compares meaning, not spelling.

"twenty milligrams" == "20 mg", "half a milligram" == "0.5 mg",
"once a day in the morning" == "once daily", "Klonopin" == "clonazepam".
"""

from __future__ import annotations

import re

from intake.tools.formulary import Formulary  # shared with the lookup tool so both sides agree on names

__all__ = ["Formulary", "norm_dose", "norm_freq", "norm_text", "words_to_number"]

_UNITS = {
    "mg": "mg", "milligram": "mg", "milligrams": "mg", "milligramme": "mg",
    "mcg": "mcg", "microgram": "mcg", "micrograms": "mcg", "µg": "mcg", "ug": "mcg",
    "g": "g", "gram": "g", "grams": "g",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "unit": "units", "units": "units", "iu": "iu",
    "tablet": "tablet", "tablets": "tablet", "tab": "tablet", "tabs": "tablet",
    "puff": "puff", "puffs": "puff", "drop": "drop", "drops": "drop", "capsule": "capsule", "capsules": "capsule",
}

_SMALL = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
          "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_FRACTIONS = {"half": 0.5, "quarter": 0.25}
_COUNT_PHRASES = [(r"\ba couple of\b|\bcouple of\b|\ba couple\b|\bcouple\b", "two")]


def words_to_number(text: str) -> str:
    """Replace number words in text with digits. 'twenty milligrams' -> '20 milligrams'."""
    text = text.lower()
    for pat, rep in _COUNT_PHRASES:
        text = re.sub(pat, rep, text)
    tokens = re.split(r"(\s+|-)", text)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in _FRACTIONS:
            out.append(str(_FRACTIONS[t]) + " ")
            # drop a following "a"/"of a"
            j = i + 1
            while j < len(tokens) and tokens[j].strip() in ("", "a", "of", "an"):
                j += 1
            i = j
            continue
        if t in _SMALL or t in _TENS or t == "hundred":
            total = 0
            current = 0
            j = i
            while j < len(tokens):
                w = tokens[j]
                if w.strip() == "" or w == "-":
                    j += 1
                    continue
                if w in _SMALL:
                    current += _SMALL[w]
                elif w in _TENS:
                    current += _TENS[w]
                elif w == "hundred":
                    current = max(current, 1) * 100
                elif w == "thousand":
                    total += max(current, 1) * 1000
                    current = 0
                elif w == "and" and current:
                    pass
                else:
                    break
                j += 1
            # "point five"
            val = total + current
            if j < len(tokens) and tokens[j] == "point":
                k = j + 1
                digits = ""
                while k < len(tokens):
                    w = tokens[k]
                    if w.strip() == "":
                        k += 1
                        continue
                    if w in _SMALL and _SMALL[w] < 10:
                        digits += str(_SMALL[w])
                        k += 1
                    else:
                        break
                if digits:
                    val = float(f"{val}.{digits}")
                    j = k
            out.append(str(val))
            out.append(" ")
            i = j
            continue
        out.append(t)
        i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip()


def norm_dose(s: str) -> str:
    """'twenty milligrams' -> '20 mg'; '' -> ''."""
    if not s or not s.strip():
        return ""
    s = words_to_number(s.lower())
    s = s.replace("milligrammes", "mg")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([a-zµ]+)?", s)
    if not m:
        return s.strip()
    num = float(m.group(1))
    num_s = str(int(num)) if num.is_integer() else str(num)
    unit = _UNITS.get((m.group(2) or "").strip(), (m.group(2) or "").strip())
    return f"{num_s} {unit}".strip()


_FREQ_RULES = [
    (r"\b(as needed|when needed|prn|if needed|when i need)\b", "as needed"),
    (r"\b(three times|3 times|thrice|tid)\b", "three times daily"),
    (r"\b(four times|4 times|qid)\b", "four times daily"),
    (r"\b(twice|two times|2 times|bid)\b", "twice daily"),
    (r"\b(weekly|once a week|every week|each week)\b", "weekly"),
    (r"\b(at night|every night|nightly|at bedtime|before bed|each night|in the evening|every evening)\b", "nightly"),
    (r"\b(once a day|once daily|daily|every day|each day|once per day|1 time a day|one time a day|in the morning|every morning|each morning|per day|mornings?|at breakfast)\b", "once daily"),
]


def norm_freq(s: str) -> str:
    if not s or not s.strip():
        return ""
    s = words_to_number(s.lower())
    for pat, canon in _FREQ_RULES:
        if re.search(pat, s):
            return canon
    return s.strip()


def norm_text(s: str) -> str:
    """Lowercase, numbers as digits, punctuation stripped but decimals kept."""
    t = words_to_number(s.lower())
    t = re.sub(r"(?<=\d)\.(?=\d)", "<dot>", t)
    t = re.sub(r"[^a-z0-9 <>]", " ", t)
    return re.sub(r"\s+", " ", t.replace("<dot>", ".")).strip()
