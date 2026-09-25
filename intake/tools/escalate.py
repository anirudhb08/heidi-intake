"""escalate_to_human: flag a red-flag symptom for an urgent nurse callback.

The `urgency` argument drives a nurse queue, so its definition matters more
than it looks. In the first evaluation the agent escalated ongoing stroke
symptoms correctly in speech 10/10 times but passed "today" instead of "now"
4/10 times, because "now" read as "just started". The description below was
rewritten to define "now" as "present at the time of the call", and the error
went to 0/10. Argument text is prompt.
"""

from __future__ import annotations

from typing import Annotated, Literal

from line.llm_agent import loopback_tool

from intake.session import CallSession


class EscalateTool:
    def __init__(self, session: CallSession):
        self.session = session

    @loopback_tool
    async def escalate_to_human(
        self,
        ctx,
        reason: Annotated[str, "Short description of why a person needs to call back"],
        urgency: Annotated[Literal["now", "today"], "'now' if the symptom is present at the time of this call, including one that started earlier and is still going on. 'today' only if the symptom has fully stopped or the patient is asking for a callback about something that is over."],
        symptom_quote: Annotated[str, "The patient's own words that triggered the escalation"],
    ) -> dict:
        """Flag the call for an urgent nurse callback. Use immediately for any red-flag
        symptom (chest pain, trouble breathing, stroke signs, severe bleeding, allergic
        reaction, thoughts of self-harm) or if the patient asks for a person. After
        calling this, do not ask further intake questions."""
        current_session = self.session
        current_session.escalated = True
        current_session.escalation = {"reason": reason, "urgency": urgency, "symptom_quote": symptom_quote}
        current_session.log("tool", tool="escalate_to_human", args=current_session.escalation, result="callback_scheduled")
        return {
            "callback_scheduled": True,
            "instruction": (
                "Tell the patient a nurse will call them back shortly on the number on file. "
                + ("If it is happening right now, tell them to call emergency services. " if urgency == "now" else "")
                + "Do not ask any more intake questions. Do not comment on how serious it is. "
                  "Say goodbye and call end_call in the same turn."
            ),
        }
