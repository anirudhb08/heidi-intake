"""Heidi Health pre-visit intake agent.

Package layout, in the order a reader should open the files:

    config.py        model, provider and timing settings, read from the environment
    prompt.py        the system prompt and the introduction line
    session.py       per-call state (verification, escalation, what was recorded)
    tools/           one file per tool, plus the shared formulary and helpers
    factory.py       build_agent(): wires prompt + tools + session into a Line LlmAgent
    guards.py        dead-air guard and call logging around the agent

Design rule that runs through all of it: anything safety-critical is enforced in
code (session + tools), and the prompt is only asked to behave well. The prompt
can drift between model versions; a tool that refuses to save an unverified
record cannot.
"""

from intake.factory import build_agent

__all__ = ["build_agent"]
