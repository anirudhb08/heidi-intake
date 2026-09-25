"""Heidi Health pre-visit intake agent on Cartesia Line."""

from __future__ import annotations

import os
from typing import AsyncIterable

from line import AgentEnv, CallRequest, CallStarted, InputEvent, OutputEvent, TurnEnv, VoiceAgentApp
from line.events import AgentEndCall, AgentSendText, AgentToolCalled, AgentToolReturned, AgentUpdateCall, UserTurnEnded
from line.llm_agent import LlmAgent, LlmConfig, end_call

from prompt import INTRODUCTION, build_system_prompt
from session import CallSession
from tools import IntakeTools

DEFAULT_MODEL = "moonshot/kimi-k2.6"

_KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "moonshot": "MOONSHOT_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}


def provider_extras(model: str) -> dict:
    """Provider-specific request options.

    Kimi K2.6 is a reasoning model. With thinking on, time to first text was
    1.5 to 9 seconds and the 300-token cap was regularly consumed by hidden
    reasoning, leaving the agent silent. Disabling thinking brings first text
    to about 1 second. Set THINKING=on to re-enable for comparison runs.
    """
    if model.startswith("moonshot/") and os.getenv("THINKING", "off").lower() != "on":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    return {}


def resolve_api_key(model: str) -> str | None:
    """LLM_API_KEY wins; otherwise the provider-specific variable for the model's prefix."""
    provider = model.split("/", 1)[0].lower() if "/" in model else "openai"
    return os.getenv("LLM_API_KEY") or os.getenv(_KEY_ENV.get(provider, "LLM_API_KEY"))

SILENT_TURN_FALLBACK = "Sorry, I didn't catch that. Could you say it again?"
SLOW_TURN_FILLER = "One moment."
SLOW_TURN_AFTER_S = float(os.getenv("FILLER_AFTER_S", "2.5"))

END_CALL_DESCRIPTION = """Ends the conversation and hangs up.

Use ONLY after you have said goodbye, and only when one of these is true:
- record_intake has been saved and you have told the patient what happens next
- escalate_to_human has been called and you have told the patient a nurse will call back
- verify_patient has failed twice and you have apologised
- the patient clearly asks to stop

Never call this without a goodbye in the same turn."""


def build_agent(session: CallSession, model: str | None = None, api_key: str | None = None) -> tuple[LlmAgent, IntakeTools]:
    """Build the LlmAgent and its tools for one call. Shared by main and the eval harness."""
    tools = IntakeTools(session)
    model = model or os.getenv("MODEL", DEFAULT_MODEL)
    agent = LlmAgent(
        model=model,
        api_key=api_key or resolve_api_key(model),
        tools=[*tools.all(), end_call(description=END_CALL_DESCRIPTION)],
        config=LlmConfig(
            system_prompt=build_system_prompt(),
            introduction=INTRODUCTION,
            max_tokens=300,
            num_retries=2,  # more retries turned rate limits into 8-second silences on a live call
            extra=provider_extras(model),
            # Kimi only accepts temperature=1, so it is sent only when set explicitly.
            **({"temperature": float(os.environ["TEMPERATURE"])} if os.getenv("TEMPERATURE") else {}),
        ),
    )
    return agent, tools


async def _with_filler(agen, enabled: bool):
    """Yield the agent's events; if the first spoken text takes longer than
    SLOW_TURN_AFTER_S (a slow provider or a retry), speak a short filler first
    so the caller never hears dead air."""
    import asyncio

    it = agen.__aiter__()
    pending = asyncio.ensure_future(it.__anext__())
    first_text_seen = False
    while True:
        if enabled and not first_text_seen:
            done, _ = await asyncio.wait({pending}, timeout=SLOW_TURN_AFTER_S)
            if not done:
                yield AgentSendText(text=SLOW_TURN_FILLER)
                first_text_seen = True  # only one filler per turn
                continue
        try:
            out = await pending
        except StopAsyncIteration:
            return
        if isinstance(out, AgentSendText) and out.text.strip():
            first_text_seen = True
        yield out
        pending = asyncio.ensure_future(it.__anext__())


async def get_agent(env: AgentEnv, call_request: CallRequest):
    session = CallSession(call_id=call_request.call_id)
    session.log("call_started", from_=call_request.from_, to=call_request.to)
    agent, _ = build_agent(session)
    voice_id = os.getenv("VOICE_ID")

    async def logged_agent(turn_env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, UserTurnEnded):
            session.log("user", text=" ".join(getattr(c, "content", "") for c in event.content))
        if isinstance(event, CallStarted) and voice_id:
            yield AgentUpdateCall(voice_id=voice_id)
        spoke = False
        ended = False
        async for out in _with_filler(agent.process(turn_env, event), isinstance(event, UserTurnEnded)):
            if isinstance(out, AgentSendText):
                spoke = spoke or bool(out.text.strip())
                session.log("agent", text=out.text)
            elif isinstance(out, AgentToolCalled):
                session.log("tool_called", tool=out.tool_name, args=out.tool_args)
            elif isinstance(out, AgentEndCall):
                ended = True
                session.log("end_call", reason=out.reason)
            yield out
        # Dead-air guard: a user turn must always get a spoken reply.
        if isinstance(event, UserTurnEnded) and not spoke and not ended:
            session.log("guard", kind_detail="silent_turn_fallback")
            yield AgentSendText(text=SILENT_TURN_FALLBACK)

    return logged_agent


app = VoiceAgentApp(get_agent=get_agent)

if __name__ == "__main__":
    app.run()
