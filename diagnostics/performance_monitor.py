"""
gesturedrive.diagnostics.performance_monitor
=============================================
PerformanceMonitor: periodic CPU and memory usage sampling.

Uses ``psutil`` to sample process-level CPU and RSS memory on a
background timer thread. Samples are stored in a rolling deque and
exposed as properties for the UI diagnostics panel.

Dependency: psutil (add to requirements.txt)
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Deque, Optional, Tuple

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Periodically samples CPU% and RSS memory usage.

    Parameters
    ----------
    interval_seconds:
        How often to sample, in seconds. Default 5.0.
    history_length:
        Number of samples to retain in the rolling history.
    """

    def __init__(
        self,
        interval_seconds: float = 5.0,
        history_length: int = 12,
    ) -> None:
        self._interval = interval_seconds
        self._cpu_history: Deque[float] = collections.deque(maxlen=history_length)
        self._mem_history: Deque[int] = collections.deque(maxlen=history_length)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Begin periodic sampling in a daemon thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="GestureDrive-PerfMonitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the sampling thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    @property
    def current_cpu_percent(self) -> float:
        """Most recent CPU% sample. 0.0 if no samples yet."""
        return self._cpu_history[-1] if self._cpu_history else 0.0

    @property
    def current_memory_mb(self) -> float:
        """Most recent RSS memory in MB. 0.0 if no samples yet."""
        return (self._mem_history[-1] / 1_048_576) if self._mem_history else 0.0

    def _run(self) -> None:
        """Daemon thread: sample psutil at each interval."""
        raise NotImplementedError
