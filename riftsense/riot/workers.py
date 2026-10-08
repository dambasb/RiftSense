from __future__ import annotations

import threading
from enum import Enum
from typing import Any, Callable


class RiotWorkerOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RiotWorkerTerminal:
    """Publish at most one terminal result for one background worker run."""

    def __init__(
        self,
        result_queue: Any,
        generation: int,
        workflow: str,
        *,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.result_queue = result_queue
        self.generation = int(generation)
        self.workflow = str(workflow)
        self._log = log or (lambda _message: None)
        self._lock = threading.Lock()
        self._sent = False

    @property
    def sent(self) -> bool:
        with self._lock:
            return self._sent

    def publish(
        self,
        outcome: RiotWorkerOutcome | str,
        message: str,
        **payload: Any,
    ) -> bool:
        try:
            outcome = RiotWorkerOutcome(outcome)
            result = dict(payload)
            result.update({
                "outcome": outcome.value,
                "generation": self.generation,
                "message": str(message or ""),
            })
        except Exception as exc:
            self._log(
                f"{self.workflow} terminal result preparation failed: "
                f"{type(exc).__name__}"
            )
            return False

        with self._lock:
            if self._sent:
                return False
            try:
                self.result_queue.put_nowait(result)
            except Exception as exc:
                self._log(
                    f"{self.workflow} terminal delivery failed: "
                    f"{type(exc).__name__}"
                )
                return False
            self._sent = True
            return True

