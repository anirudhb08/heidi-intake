"""Code-level safety net around the agent's event stream.

`wrap_agent` returns the callable Line drives (any `(turn_env, event) ->
AsyncIterable[OutputEvent]` is a valid agent; see line/agent.py). It forwards
every event the LlmAgent yields, logs user text, agent text, tool calls and
hangups on the session, and applies one guard:

  dead-air guard   a user turn that produced no spoken text and no hangup gets
                   a fallback line. Found when a reasoning model consumed the
                   whole reply budget on hidden thinking and said nothing, with
                   no error raised.

Not used by the evaluation harness, which calls `agent.process` directly: the
guard protects the audio path; the harness measures the reasoning.
"""

from __future__ import annotations

from typing import AsyncIterable, Callable

from line import InputEvent, OutputEvent, TurnEnv
from line.events import AgentEndCall, AgentSendText, AgentToolCalled, UserTurnEnded
from line.llm_agent import LlmAgent

from intake import config
from intake.session import CallSession


def wrap_agent(agent: LlmAgent, session: CallSession) -> Callable[[TurnEnv, InputEvent], AsyncIterable[OutputEvent]]:
    async def guarded(turn_env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        is_user_turn = isinstance(event, UserTurnEnded)
        if is_user_turn:
            session.log("user", text=" ".join(getattr(c, "content", "") for c in event.content))

        spoke = False
        ended = False
        async for out in agent.process(turn_env, event):
            if isinstance(out, AgentSendText):
                spoke = spoke or bool(out.text.strip())
                session.log("agent", text=out.text)
            elif isinstance(out, AgentToolCalled):
                session.log("tool_called", tool=out.tool_name, args=out.tool_args)
            elif isinstance(out, AgentEndCall):
                ended = True
                session.log("end_call", reason=out.reason)
            yield out  # forward unchanged, including the hangup

        if is_user_turn and not spoke and not ended:
            session.log("guard", detail="silent_turn_fallback")
            yield AgentSendText(text=config.SILENT_TURN_FALLBACK)

    return guarded
