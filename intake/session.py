"""Per-call state and a structured call log.

One `CallSession` is created per call and handed to every tool. It is the
single place where the safety-relevant facts of a call live:

  * which patient this call is for (looked up from the dialled number)
  * has the person on the line confirmed they are that patient
  * has a red flag been escalated
  * what, if anything, has been recorded

Tools read and write these fields; the prompt never sees them directly. That
is deliberate: the verification gate is `record_intake` refusing to save while
`session.verified` is false, not a sentence in the prompt asking the model to
behave.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG = ROOT / "logs" / "calls.jsonl"
DEFAULT_INTAKE_DIR = ROOT / "data" / "intakes"


@dataclass
class CallSession:
    call_id: str
    log_path: Path = DEFAULT_LOG
    intake_dir: Path = DEFAULT_INTAKE_DIR

    # The record for the number dialled. Known before the call starts.
    expected_patient: Optional[dict] = None
    # Set by confirm_patient when the person on the line says they are the
    # patient. None means the gate is closed: no details shared, nothing saved.
    verified_patient: Optional[dict] = None

    # Set by escalate_to_human. record_intake stores these on the record so a
    # partial intake taken before a red flag is not lost.
    escalated: bool = False
    escalation: Optional[dict] = None

    # Set once by record_intake. A second call returns the same id.
    recorded_intake: Optional[dict] = None

    started_at: float = field(default_factory=time.time)

    @property
    def verified(self) -> bool:
        return self.verified_patient is not None

    def log(self, kind: str, **data: Any) -> None:
        """Append one JSON line to the call log.

        `kind` is one of: call_started, user, agent, tool, tool_called,
        end_call, guard. Tool calls are logged with their full arguments so the
        harness can grade arguments directly rather than infer them from speech.
        """
        entry = {
            "ts": round(time.time() - self.started_at, 3),
            "call_id": self.call_id,
            "kind": kind,
            **data,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def write_intake(self, record: dict) -> Path:
        """Persist the intake record as one JSON file. This is the clinic hand-off
        for the exercise; production would post to Heidi's note pipeline."""
        self.intake_dir.mkdir(parents=True, exist_ok=True)
        path = self.intake_dir / f"{record['intake_id']}.json"
        path.write_text(json.dumps(record, indent=2))
        return path
