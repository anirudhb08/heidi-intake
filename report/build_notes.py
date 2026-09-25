"""Build the short agent note for an external reader: what was built, and the
known weaknesses to harden next. No evaluation results; those are in
evaluation_report.pdf.

    uv run python report/build_notes.py            # writes report/agent_notes.pdf

Content follows NOTES.md. (C) marks a claim with evidence behind it, (G) a guess.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from theme import Spacer, build_doc, bullets, callout, h1, make_doc, numbered, p, table, title_block

HERE = Path(__file__).resolve().parent
OUT = HERE / "agent_notes.pdf"


def story() -> list:
    s: list = [
        *title_block("Heidi Health pre-visit intake agent",
                     f"What was built, and what to harden next · {date.today():%d %B %Y} · the evaluation and its numbers are in the separate evaluation report"),
        callout([
            "<b>What it is:</b> a voice agent on Cartesia Line that phones a patient before an appointment, confirms it is "
            "speaking with them, collects the reason for the visit, medications, allergies and history, reads it all back, "
            "and saves a structured summary for the clinician. It never diagnoses or gives advice, hands red-flag symptoms "
            "to a nurse, and lets the patient end the call at any point.",
            "<b>Status:</b> works end to end on real calls (one is recorded). Safe in text, with evidence. Not yet ready for "
            "real patients: the voice path is only partly measured, and three known weaknesses below need closing first.",
        ]),
        Spacer(1, 10),

        *h1("What the agent does"),
        p("The clinic dials the number on file, so the patient is known before the first word. The call runs in a fixed order:"),
        *bullets([
            "<b>Introduction and identity.</b> The agent says it is an automated assistant from the clinic and asks \"Am I "
            "speaking with Maria?\". Nothing about the appointment is said, and no question asked, until the person says yes. "
            "If someone else answers, the agent says only that it was a pre-visit call, says the clinic will try again, and hangs up.",
            "<b>Four things, one question at a time.</b> Reason for the visit; every current medication with dose and how often; "
            "medication allergies; conditions, recent surgeries or hospital stays. Each medication is read back once and confirmed.",
            "<b>Readback and save.</b> The whole summary is read back in one turn, the patient corrects anything, and only then is "
            "the record saved. If the patient wants to stop early, whatever was collected is saved as incomplete and the call ends politely.",
            "<b>Boundaries.</b> A clinical question gets one warm sentence deferring it to the doctor, is added to the notes, and the "
            "next intake question follows. A red-flag symptom (chest pain, stroke signs, trouble breathing, and so on) stops the intake "
            "at once, schedules a nurse callback, and ends the call. Requests outside the intake are declined in one sentence.",
        ]),
        p("Four tools", "h2"),
        table(["Tool", "What it does"], [
            ["confirm_patient", "The identity gate. Records who answered; only a yes from the patient opens the rest of the call. The model is never given the patient's full record, only the first name and appointment."],
            ["lookup_medication", "Checks a spoken drug name against the clinic's list and flags sound-alikes. A name that could be more than one drug is never resolved by the agent: it reads the name back as said and asks which one, by what each is for. An unknown name is recorded exactly as heard, with the patient's description."],
            ["record_intake", "Saves the summary. Refuses, in code, to save anything unless identity was confirmed. A second call is a no-op."],
            ["escalate_to_human", "Flags a red-flag symptom for a nurse callback with an urgency argument (\"now\" or \"today\") and the patient's own words."],
        ], [34, 142]),
        Spacer(1, 4),
        p("Choices worth knowing about", "h2"),
        *bullets([
            "<b>The safety rules that matter most are enforced in code, not only in the prompt.</b> The record tool refuses to save "
            "before identity is confirmed; the escalation tool's urgency argument is defined in the tool, not left to the model; a "
            "dead-air guard speaks a fallback line if a turn produces no speech; a request timeout and a retry cap bound a hung provider.",
            "<b>Rules the model must follow right after a tool call live in that tool's reply.</b> \"Do not ask the dose of a cream\" and "
            "\"do not ask the patient to spell a garbled name\" both slipped as prompt rules and held once the same sentence came back from "
            "the lookup tool. The model follows tool results more literally than the system prompt.",
            "<b>Every rule in the prompt is annotated with the failure that produced it</b>, so the next person knows what breaks if it is removed.",
            "<b>Model and voice.</b> Kimi K2.6 with reasoning turned off, since hidden reasoning left callers in silence; any provider "
            "can be swapped in through one setting. Turns are capped at 35 words and numbers are spoken as words. The voice is set in the "
            "Cartesia console.",
        ]),

        *h1("Known weaknesses, in the order I would fix them"),
        p("(C) means there is evidence behind the claim, (G) means I am guessing."),
        *numbered([
            "<b>The audio path is only partly measured (C).</b> A synthetic set of 72 clips across six accents puts numbers on "
            "whether drug names survive speech-to-text; they mostly do, and a garble is now recorded as heard rather than guessed. "
            "Not measured at all: the phone codec, live turn detection, the agent's own pronunciation of drug names, latency, and real "
            "rather than synthesised accents. First step: play the same 72 clips into a live call; then real recordings as the anchor.",
            "<b>Latency failures are silent by design (C).</b> With reasoning on, the model took 1.5 to 9 seconds to first word and "
            "often spent the whole reply budget thinking, so the caller heard nothing and no error was raised. Reasoning is off, a "
            "dead-air guard and a 30-second timeout exist, but there is no latency budget in the harness yet. I would alert on any turn over 2 seconds.",
            "<b>Identity is one factor, by choice (C).</b> The outbound number is the first factor and a spoken yes is trusted; no date "
            "of birth. A household member who says yes hears the appointment and can give an intake by proxy. Before a real deployment "
            "this needs a second identifier, and the code is arranged so that is one change inside the tool that opens the gate.",
            "<b>Prompt-only rules are provisional across model versions (C).</b> Two rules slipped as prompt text and held as tool "
            "text (above). Others may do the same after a model update, which is why every case in the evaluation runs ten times.",
            "<b>A provider failure still ends in a fallback line (C).</b> Rate limits, a hung request and an exhausted account were "
            "all seen. The agent now bounds them, but does not yet apologise and arrange a callback, which is what a patient should hear.",
            "<b>Interruptions and turn-taking are untested (G).</b> The readback turns are long by voice standards. A patient who "
            "interrupts a readback to correct a dose is the most likely real-world path and is not covered.",
        ]),
        p("Accepted for this exercise", "h2"),
        p("A 61-drug medication list, so anything else is recorded as said and left to the clinician. No voicemail handling: an "
          "answering machine hears the introduction. Escalation is driven by an explicit red-flag list, so an unusual phrasing may "
          "not trigger it. Scope and instruction-override behaviour is tested with two phrasings each; a real adversary has more. "
          "The provider does not allow temperature control, so run-to-run variance is measured rather than tuned."),
        p("The clearest lesson", "h2"),
        p("In the first version the agent escalated stroke symptoms correctly in speech every time, and passed the wrong urgency to "
          "the nurse-callback tool four times in ten. A demo call would have looked perfect. Two real calls then found four problems "
          "that 130 text runs had not, because the harness had no case for a patient who was confused or done. Grade the tool "
          "arguments, and keep making real calls."),
    ]
    return s


def build() -> Path:
    doc = make_doc(OUT, "Heidi intake agent: what was built and what to harden next",
                   "Heidi Health pre-visit intake agent · what was built and what to harden next")
    build_doc(doc, story())
    return OUT


if __name__ == "__main__":
    print(build())
