"""The agent's tools, one per file.

    confirm.py    confirm_patient      identity gate; everything else waits on it
    lookup.py     lookup_medication    normalise a spoken drug name, flag sound-alikes
    record.py     record_intake        save the structured summary; refuses if unverified
    escalate.py   escalate_to_human    red-flag callback; marks the session escalated
    formulary.py  the demo drug list used by lookup (and by the evaluation normaliser)
    schema.py     TypedDicts for the record schema the model fills

Each tool is a class holding a reference to the call's `CallSession`, with a
single `@loopback_tool` method. Line's decorator supports bound methods, so
`build_tools(session)` returns the bound FunctionTools ready for `LlmAgent`.

Conventions shared by every tool:
  * `ctx` is the first parameter (Line requirement) and is unused here.
  * The return value is a plain dict; the SDK JSON-encodes it for the model.
  * Any dict may carry an `instruction` string. Tool results are prompt: the
    model follows them at least as closely as the system prompt, so the
    instruction says what to do next in the same voice as the prompt.
  * Every call is logged on the session with its arguments and result.
"""

from __future__ import annotations

from intake.session import CallSession
from intake.tools.escalate import EscalateTool
from intake.tools.formulary import Formulary
from intake.tools.lookup import LookupTool
from intake.tools.record import RecordTool
from intake.tools.confirm import ConfirmTool


def build_tools(session: CallSession, formulary: Formulary | None = None) -> list:
    """Bind all four tools to one call's session and return them for LlmAgent."""
    formulary = formulary or Formulary()
    return [
        ConfirmTool(session).confirm_patient,
        LookupTool(session, formulary).lookup_medication,
        RecordTool(session).record_intake,
        EscalateTool(session).escalate_to_human,
    ]


__all__ = ["build_tools", "Formulary", "ConfirmTool", "LookupTool", "RecordTool", "EscalateTool"]
