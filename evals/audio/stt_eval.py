"""Transcribe every clip in the audio set and score what the agent would receive.

    uv run python -m evals.audio.stt_eval                 # ink-whisper; transcripts cached per clip+model
    uv run python -m evals.audio.stt_eval --model <id>    # score a different STT model on the same audio

For each clip the manifest says which drug names and dose numbers the patient
spoke. Four things are scored against the transcript:

  drug name recognised    the drug appears, matched through the formulary (brand == generic)
  dose number recognised  the figure appears, after number words are turned into digits
  word error rate         against the manifest text, for orientation only
  lookup outcome          what the agent's lookup tool would do with the transcript:
                          EXACT, AMBIGUOUS (asks which), LOST (recorded as heard),
                          or WRONG_DRUG (a confident match onto a drug the patient did not say)

Transcripts are cached at transcripts/<hash>.<model>.json so a newer model is
scored on identical audio, never re-synthesised. Outputs:
  stt_results.<model>.jsonl   one line per clip with transcript and scores
  stt_report.<model>.md       totals, a table per accent, a table per utterance kind, every miss
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from cartesia import Cartesia  # noqa: E402

from evals.normalize import Formulary, norm_text  # noqa: E402

MANIFEST = HERE / "manifest.jsonl"
TRANSCRIPTS_DIR = HERE / "transcripts"
FORMULARY = Formulary()

EXACT, AMBIGUOUS, LOST, WRONG_DRUG = "exact", "ambiguous", "lost", "WRONG_DRUG"
MIN_FUZZY_PHRASE_LEN = 5  # a transcript token shorter than this is never a garbled drug name


# ------------------------------------------------------------------ transcription

def transcribe(client: Cartesia, clip_path: Path, model: str) -> str:
    cache = TRANSCRIPTS_DIR / f"{clip_path.stem}.{model}.json"
    if cache.exists():
        return json.loads(cache.read_text())["text"]
    with clip_path.open("rb") as audio:
        response = client.stt.transcribe(file=audio, model=model, language="en")
    cache.write_text(json.dumps({"text": response.text, "model": model}, indent=1))
    return response.text


# ------------------------------------------------------------------ scoring one clip

def candidate_phrases(transcript: str) -> list[str]:
    """Every word and every adjacent word pair, normalised. Drug names can be one
    token ("lisinopril") or two ("baby aspirin", "vitamin d")."""
    words = norm_text(transcript).split()
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]


def drug_recognised(drug: str, transcript: str) -> bool:
    wanted = FORMULARY.canon(drug)
    return any(FORMULARY.canon(phrase) == wanted for phrase in candidate_phrases(transcript))


def number_recognised(number, transcript: str) -> bool:
    return str(number) in re.findall(r"\d+(?:\.\d+)?", norm_text(transcript))


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = norm_text(reference).split(), norm_text(hypothesis).split()
    distances = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, start=1):
        previous_diagonal, distances[0] = distances[0], i
        for j, hyp_word in enumerate(hyp, start=1):
            current = min(distances[j] + 1, distances[j - 1] + 1, previous_diagonal + (ref_word != hyp_word))
            previous_diagonal, distances[j] = distances[j], current
    return distances[len(hyp)] / max(len(ref), 1)


def lookup_outcome(drug: str, transcript: str, drugs_in_utterance: set[str]) -> str:
    """Replay the lookup tool's decision on the transcript for one expected drug.

    Mirrors intake/tools/lookup.py: a single candidate is a match (confirmed with
    the patient if fuzzy); more than one candidate is ambiguous and the agent asks which.
    """
    wanted = FORMULARY.canon(drug)
    confident: set[str] = set()
    ambiguous: set[str] = set()
    for phrase in candidate_phrases(transcript):
        candidates, fuzzy = FORMULARY.match(phrase)
        candidates = {FORMULARY.canon(c) for c in candidates}
        if not candidates or (fuzzy and len(phrase) < MIN_FUZZY_PHRASE_LEN):
            continue  # the agent only looks up names it extracted, never words like "as" (close to "asa")
        if len(candidates) == 1:
            confident |= candidates
        else:
            ambiguous |= candidates
    if wanted in confident:
        return EXACT
    wrong = sorted(confident - drugs_in_utterance)
    if wrong:
        return f"{WRONG_DRUG}:{','.join(wrong)}"
    if wanted in ambiguous:
        return AMBIGUOUS
    return LOST


@dataclass
class ClipScore:
    clip: dict
    transcript: str
    drug_hits: list[bool]
    number_hits: list[bool]
    outcomes: list[str]
    wer: float

    @property
    def misses(self) -> list[tuple[str, str]]:
        """(expected drug, lookup outcome) for each drug not recognised exactly."""
        return [(d, o) for d, hit, o in zip(self.clip["drugs"], self.drug_hits, self.outcomes) if not hit]

    def to_dict(self) -> dict:
        return {**self.clip, "transcript": self.transcript, "drug_hits": self.drug_hits,
                "number_hits": self.number_hits, "lookup_outcomes": self.outcomes, "wer": round(self.wer, 3)}


def score_clip(clip: dict, transcript: str) -> ClipScore:
    drugs_in_utterance = {FORMULARY.canon(d) for d in clip["drugs"]}
    return ClipScore(
        clip=clip,
        transcript=transcript,
        drug_hits=[drug_recognised(d, transcript) for d in clip["drugs"]],
        number_hits=[number_recognised(n, transcript) for n in clip["numbers"]],
        outcomes=[lookup_outcome(d, transcript, drugs_in_utterance) for d in clip["drugs"]],
        wer=word_error_rate(clip["text"], transcript),
    )


# ------------------------------------------------------------------ report

@dataclass
class Tally:
    drugs_hit: int = 0
    drugs_total: int = 0
    numbers_hit: int = 0
    numbers_total: int = 0
    wer_sum: float = 0.0
    clips: int = 0

    def add(self, s: ClipScore) -> None:
        self.drugs_hit += sum(s.drug_hits)
        self.drugs_total += len(s.drug_hits)
        self.numbers_hit += sum(s.number_hits)
        self.numbers_total += len(s.number_hits)
        self.wer_sum += s.wer
        self.clips += 1

    def row(self, label: str) -> str:
        return f"| {label} | {self.drugs_hit}/{self.drugs_total} | {self.numbers_hit}/{self.numbers_total} | {self.wer_sum / self.clips:.2f} | {self.clips} |"


def table_by(scores: list[ClipScore], key: str) -> str:
    tallies: dict[str, Tally] = defaultdict(Tally)
    for s in scores:
        tallies[s.clip[key]].add(s)
    header = [f"| {key} | drug names | dose numbers | mean WER | clips |", "|---|---|---|---|---|"]
    return "\n".join(header + [tallies[label].row(label) for label in sorted(tallies)])


def build_report(scores: list[ClipScore], model: str) -> str:
    overall = Tally()
    for s in scores:
        overall.add(s)
    outcome_counts = Counter(o.split(":")[0] for s in scores for o in s.outcomes)
    misses = [f"- {s.clip['accent']} ({s.clip['voice']}): expected **{drug}**, lookup -> {outcome}, heard: \"{s.transcript}\""
              for s in scores for drug, outcome in s.misses]
    return "\n".join([
        f"# STT evaluation: `{model}` on {len(scores)} clips", "",
        f"Drug names recognised exactly: **{overall.drugs_hit}/{overall.drugs_total}**. "
        f"Dose numbers recognised: **{overall.numbers_hit}/{overall.numbers_total}**. "
        f"Mean WER {overall.wer_sum / overall.clips:.2f}.", "",
        f"After the agent's lookup: exact {outcome_counts[EXACT]}, "
        f"ambiguous (asks which, or records as heard with candidates) {outcome_counts[AMBIGUOUS]}, "
        f"lost (recorded as heard) {outcome_counts[LOST]}, "
        f"**mapped to a wrong drug {outcome_counts[WRONG_DRUG]}** of {overall.drugs_total}.", "",
        "## By accent", "", table_by(scores, "accent"), "",
        "## By utterance kind", "", table_by(scores, "kind"), "",
        "## Every drug-name miss", "",
        *(misses or ["- none"]),
    ]) + "\n"


# ------------------------------------------------------------------ entry point

def main(model: str) -> None:
    client = Cartesia(api_key=os.environ["CARTESIA_API_KEY"])
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    clips = [json.loads(line) for line in MANIFEST.read_text().splitlines()]
    scores = [score_clip(clip, transcribe(client, HERE / clip["file"], model)) for clip in clips]

    (HERE / f"stt_results.{model}.jsonl").write_text("\n".join(json.dumps(s.to_dict()) for s in scores) + "\n")
    report = build_report(scores, model)
    (HERE / f"stt_report.{model}.md").write_text(report)
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="ink-whisper")
    main(parser.parse_args().model)
