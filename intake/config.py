"""Runtime configuration, all overridable from the environment.

Nothing here is secret. API keys are read at call time by `resolve_api_key`.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------- model

#: LiteLLM model id, "<provider>/<model>". Kimi K2.6 is the default because it
#: is the key available for this exercise. Any LiteLLM provider works; the
#: harness and the deployment read the same value.
DEFAULT_MODEL = os.getenv("MODEL", "moonshot/kimi-k2.6")

#: Hard cap on tokens per agent turn. Voice turns are short; 300 is generous for
#: a 35-word reply plus a tool call, and it bounds the cost of a runaway turn.
MAX_TOKENS = 300

#: LiteLLM-level retries. This was 5 during evaluation after provider rate
#: limits, and that turned one throttled request into an 8-second silence on a
#: real call. Two is the compromise; REQUEST_TIMEOUT_S bounds each attempt.
NUM_RETRIES = 2

#: Seconds before a single model request is abandoned and retried. Without it
#: a hung provider request held an evaluation slot for over an hour; on a live
#: call it would be unbounded silence.
REQUEST_TIMEOUT_S = 30

#: Which environment variable holds the key for each provider prefix.
#: LLM_API_KEY always wins if set, so one variable can drive any provider.
_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def resolve_api_key(model: str) -> str | None:
    """Return the API key for the model's provider prefix."""
    provider = model.split("/", 1)[0].lower() if "/" in model else "openai"
    return os.getenv("LLM_API_KEY") or os.getenv(_KEY_ENV.get(provider, "LLM_API_KEY"))


def provider_extras(model: str) -> dict:
    """Provider-specific request options passed through LiteLLM.

    Kimi K2.6 is a reasoning model. With thinking on, time to first text was
    1.5 to 9 seconds and the 300-token cap was regularly consumed by hidden
    reasoning, so the agent went silent with no error raised. Disabling
    thinking brings first text to about 1 second. Set THINKING=on to compare.
    """
    if model.startswith("moonshot/") and os.getenv("THINKING", "off").lower() != "on":
        return {"extra_body": {"thinking": {"type": "disabled"}}}
    return {}


# No temperature is sent: Moonshot accepts only 1 for Kimi, so the provider
# default is used and run-to-run variance is measured rather than tuned.

# ---------------------------------------------------------------- identity

#: Outbound calls dial the number on file, so the patient is known before the
#: first word. Calls from a number not on file (the web playground reports
#: "websocket") fall back to this patient so demos and recordings work.
#: Production would refuse the call instead.
DEFAULT_PATIENT_ID = os.getenv("DEFAULT_PATIENT_ID", "pt_001")

# ---------------------------------------------------------------- guards

#: Spoken by the dead-air guard when a user turn produced no reply and no hangup.
SILENT_TURN_FALLBACK = "Sorry, I didn't catch that. Could you say it again?"
