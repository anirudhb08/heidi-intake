"""Heidi Health pre-visit intake agent: Cartesia Line entry point.

Run locally:      PORT=8000 uv run python main.py   then   cartesia chat 8000
Deploy:           cartesia deploy --agent-id <id>

Everything interesting lives in the `intake` package. This file only works out
which patient the call is for, creates a session, builds the agent, and hands
Line the guarded callable.
"""

from __future__ import annotations

from line import AgentEnv, CallRequest, VoiceAgentApp

from intake import config, patients
from intake.factory import build_agent
from intake.guards import wrap_agent
from intake.session import CallSession


async def get_agent(env: AgentEnv, call_request: CallRequest):
    # Outbound: `to` is the patient's number. Inbound or web: try `from`.
    # Neither on file (the playground reports "websocket"): use the demo patient.
    patient = (
        patients.by_phone(call_request.to)
        or patients.by_phone(call_request.from_)
        or patients.by_id(config.DEFAULT_PATIENT_ID)
    )
    session = CallSession(call_id=call_request.call_id, expected_patient=patient)
    session.log("call_started", from_=call_request.from_, to=call_request.to,
                patient_id=patient["patient_id"] if patient else None)
    return wrap_agent(build_agent(session), session)


app = VoiceAgentApp(get_agent=get_agent)

if __name__ == "__main__":
    app.run()
