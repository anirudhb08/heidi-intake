"""build_agent(): the one place that wires prompt, tools, session and model together.

Used by both the deployment (`main.py`) and the evaluation harness
(`evals/simulate.py`), so what is evaluated is exactly what is deployed.
"""

from __future__ import annotations

from line.llm_agent import LlmAgent, LlmConfig, end_call

from intake import config
from intake.prompt import build_introduction, build_system_prompt
from intake.session import CallSession
from intake.tools import build_tools

#: The built-in end_call tool with a description that lists the only situations
#: in which hanging up is allowed. The SDK default is "when the user says
#: goodbye"; ours also covers escalation, failed verification, and the patient
#: asking to stop, and insists on a goodbye in the same turn.
END_CALL_DESCRIPTION = """Ends the conversation and hangs up.

Use ONLY after you have said goodbye, and only when one of these is true:
- record_intake has been saved and you have told the patient what happens next
- escalate_to_human has been called and you have told the patient a nurse will call back
- confirm_patient returned matched=false and you have said the clinic will try again
- the patient says goodbye, says they have to go, or asks to stop

Never call this without a goodbye in the same turn."""


def build_agent(session: CallSession, model: str | None = None) -> LlmAgent:
    """Return the agent for one call. `model` defaults to the environment (see intake/config.py)."""
    model = model or config.DEFAULT_MODEL
    first_name = session.expected_patient["first_name"] if session.expected_patient else None
    return LlmAgent(
        model=model,
        api_key=config.resolve_api_key(model),
        tools=[*build_tools(session), end_call(description=END_CALL_DESCRIPTION)],
        config=LlmConfig(
            system_prompt=build_system_prompt(first_name),
            introduction=build_introduction(first_name),
            max_tokens=config.MAX_TOKENS,
            num_retries=config.NUM_RETRIES,
            timeout=config.REQUEST_TIMEOUT_S,
            extra=config.provider_extras(model),
        ),
    )
