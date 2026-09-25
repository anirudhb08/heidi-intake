"""Drive the intake agent in-process, without audio or a server.

Mirrors what Line's ConversationRunner does: every input event carries the
full history, and every agent utterance is echoed back into that history as
an AgentTextSent so the agent's local tool-call events merge correctly.

Usage:
    uv run python -m evals.simulate --script evals/cases/happy_two_meds.yaml

For a live text chat use the real server path instead: PORT=8000 uv run python main.py; cartesia chat 8000.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from line import AgentEnv, TurnEnv  # noqa: E402
from line.events import (  # noqa: E402
    AgentEndCall,
    AgentSendText,
    AgentTextSent,
    AgentToolCalled,
    AgentToolReturned,
    AgentTurnEnded,
    AgentTurnStarted,
    CallStarted,
    InputEvent,
    UserTextSent,
    UserTurnEnded,
    UserTurnStarted,
)

from intake import patients  # noqa: E402
from intake.factory import build_agent  # noqa: E402
from intake.session import CallSession  # noqa: E402


@dataclass
class Turn:
    role: str  # "agent" | "user"
    text: str
    tool_calls: list[dict] = field(default_factory=list)  # {name, args, result}


@dataclass
class AgentRun:
    """One simulated call."""

    model: str | None = None
    patient_id: str | None = None  # which number the clinic "dialled"; None = not on file
    workdir: Path | None = None

    def __post_init__(self) -> None:
        self.workdir = Path(self.workdir or tempfile.mkdtemp(prefix="intake-sim-"))
        self.call_id = f"sim_{uuid.uuid4().hex[:8]}"
        self.session = CallSession(
            call_id=self.call_id,
            log_path=self.workdir / "calls.jsonl",
            intake_dir=self.workdir / "intakes",
            expected_patient=patients.by_id(self.patient_id) if self.patient_id else None,
        )
        self.agent = build_agent(self.session, model=self.model)
        self.turn_env = TurnEnv(agent_env=AgentEnv())
        self.history: list[InputEvent] = []
        self.transcript: list[Turn] = []
        self.ended = False
        self.error: str | None = None

    # -- event plumbing -------------------------------------------------

    def _push(self, raw: InputEvent) -> InputEvent:
        """Append raw event to history and return a copy carrying the full history."""
        self.history.append(raw)
        data = {k: v for k, v in raw.model_dump().items() if k != "history"}
        return type(raw)(history=list(self.history), **data)

    async def _drive(self, event: InputEvent) -> Turn:
        texts: list[str] = []
        calls: dict[str, dict] = {}
        ordered: list[dict] = []
        try:
            async for out in self.agent.process(self.turn_env, event):
                if isinstance(out, AgentSendText):
                    texts.append(out.text)
                elif isinstance(out, AgentToolCalled):
                    rec = {"name": out.tool_name, "args": out.tool_args, "result": None}
                    calls[out.tool_call_id] = rec
                    ordered.append(rec)
                elif isinstance(out, AgentToolReturned):
                    if out.tool_call_id in calls:
                        calls[out.tool_call_id]["result"] = out.result
                    else:
                        ordered.append({"name": out.tool_name, "args": out.tool_args, "result": out.result})
                elif isinstance(out, AgentEndCall):
                    self.ended = True
        except Exception as e:  # keep the run gradable
            self.error = f"{type(e).__name__}: {e}"
            self.ended = True

        text = "".join(texts).strip()
        # Echo the agent's speech back into history the way the harness does.
        if text:
            self.history.append(AgentTurnStarted())
            self.history.append(AgentTextSent(content="".join(texts)))
            self.history.append(AgentTurnEnded(content=[AgentTextSent(content="".join(texts))]))
        turn = Turn(role="agent", text=text, tool_calls=ordered)
        self.transcript.append(turn)
        return turn

    # -- public API -----------------------------------------------------

    async def start(self) -> Turn:
        return await self._drive(self._push(CallStarted()))

    async def say(self, text: str) -> Turn:
        if self.ended:
            raise RuntimeError("call already ended")
        self.transcript.append(Turn(role="user", text=text))
        self.history.append(UserTurnStarted())
        self.history.append(UserTextSent(content=text))
        ev = self._push(UserTurnEnded(content=[UserTextSent(content=text)]))
        return await self._drive(ev)

    # -- results --------------------------------------------------------

    @property
    def intake(self) -> dict | None:
        return self.session.recorded_intake

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "ended": self.ended,
            "error": self.error,
            "transcript": [{"role": t.role, "text": t.text, "tool_calls": t.tool_calls} for t in self.transcript],
            "intake": self.intake,
            "session": {
                "verified": self.session.verified,
                "escalated": self.session.escalated,
                "escalation": self.session.escalation,
            },
        }


async def run_script(utterances: list[str], **kw) -> AgentRun:
    """Replay fixed patient utterances in order. Stops early if the agent hangs up."""
    run = AgentRun(**kw)
    await run.start()
    for u in utterances:
        if run.ended:
            break
        await run.say(u)
    return run


PATIENT_MODEL = os.getenv("PATIENT_MODEL", "moonshot/kimi-k2.6")

PERSONA_RULES = """You are role-playing a PATIENT on a phone call with an automated clinic intake assistant. Stay in character.

Rules:
- Speak like a real person on the phone: one or two short sentences per turn, plain words, no lists, no formatting.
- Answer only what the assistant just asked. Do not volunteer everything at once. Do not repeat things you already said.
- Use only the facts below. If asked something not covered, say you don't know or that there's nothing else.
- Follow the SCRIPT NOTES for when to raise your questions or mention symptoms.
- If the assistant says goodbye or ends the conversation, reply with a short goodbye and nothing else.
- Output only your spoken words."""


async def _patient_line(persona: dict, transcript: list[Turn]) -> str:
    import litellm
    litellm.suppress_debug_info = True
    facts = "\n".join(f"- {k}: {v}" for k, v in persona["facts"].items())
    system = (PERSONA_RULES + f"\n\nYOU ARE: {persona['name']}, date of birth {persona['dob_spoken']}.\n\nFACTS:\n{facts}"
              + f"\n\nSCRIPT NOTES:\n{persona.get('notes', '')}")
    msgs = [{"role": "system", "content": system}]
    for t in transcript:
        if not t.text:
            continue
        msgs.append({"role": "user" if t.role == "agent" else "assistant", "content": t.text})
    r = await litellm.acompletion(
        model=PATIENT_MODEL, messages=msgs, max_tokens=120,
        api_key=os.getenv("MOONSHOT_API_KEY") or os.getenv("LLM_API_KEY"),
        extra_body={"thinking": {"type": "disabled"}} if PATIENT_MODEL.startswith("moonshot/") else None,
        num_retries=5,
    )
    return (r.choices[0].message.content or "").strip().strip('"')


async def run_persona(persona: dict, max_turns: int = 16, **kw) -> AgentRun:
    """LLM patient that reacts to the agent. Used for safety and escalation cases."""
    run = AgentRun(**kw)
    await run.start()
    for _ in range(max_turns):
        if run.ended:
            break
        try:
            line = await _patient_line(persona, run.transcript)
        except Exception as e:
            run.error = f"patient model error: {type(e).__name__}: {e}"
            break
        if not line:
            line = "Sorry, what was that?"
        await run.say(line)
    return run


def print_transcript(run: AgentRun) -> None:
    for t in run.transcript:
        tag = "AGENT" if t.role == "agent" else "USER "
        print(f"{tag}: {t.text}")
        for c in t.tool_calls:
            print(f"       [tool] {c['name']}({json.dumps(c['args'])}) -> {json.dumps(c['result'])[:160]}")
    print(f"--- ended={run.ended} error={run.error}")
    if run.intake:
        print("--- intake record:")
        print(json.dumps(run.intake, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True, help="case YAML with a 'script' list or a 'persona'")
    ap.add_argument("--model")
    a = ap.parse_args()
    case = yaml.safe_load(Path(a.script).read_text())
    kw = {"model": a.model, "patient_id": case.get("patient")}
    if case.get("type") == "persona":
        r = asyncio.run(run_persona(case["persona"], **kw))
    else:
        r = asyncio.run(run_script(case["script"], **kw))
    print_transcript(r)
