"""
gesturedrive.core.event_bus
============================
Thread-safe in-process publish/subscribe event bus.

Design
------
- Handlers are registered per *event class* (not string topics).
- Synchronous delivery for low-latency pipeline events (camera → controller).
- Optional async queued delivery for UI updates (prevents blocking camera thread).
- A wildcard ``ErrorEvent`` handler is always subscribed automatically.
- No external dependencies — pure stdlib (threading + queue).

Usage
-----
    bus = EventBus()

    # Subscribe
    bus.subscribe(GestureRecognizedEvent, my_handler)

    # Publish (synchronous)
    bus.publish(GestureRecognizedEvent(source="gesture.service", result_set=rs))

    # Publish to UI queue (non-blocking)
    bus.publish_async(HandDetectedEvent(source="tracking.service", hand_state=hs))
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Dict, List, Type, TypeVar

from core.events import BaseEvent, ErrorEvent

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseEvent)
Handler = Callable[[BaseEvent], None]


class EventBus:
    """
    Central in-process publish/subscribe event bus.

    Attributes
    ----------
    _handlers:      Maps event class → list of synchronous handler callables.
    _async_queue:   Queue for UI-bound events processed on the UI thread.
    _lock:          Guards handler registration against concurrent mutation.
    """

    def __init__(self) -> None:
        self._handlers: Dict[Type[BaseEvent], List[Handler]] = {}
        self._async_queue: queue.Queue[BaseEvent] = queue.Queue()
        self._lock = threading.Lock()

    # ── Subscription ──────────────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: Type[T],
        handler: Callable[[T], None],
    ) -> None:
        """
        Register ``handler`` to be called synchronously whenever an event of
        ``event_type`` is published.

        Thread-safe: may be called from any thread before or after start-up.
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)  # type: ignore[arg-type]
        logger.debug(
            "Subscribed %s.%s to %s",
            handler.__module__,
            handler.__qualname__,
            event_type.__name__,
        )

    def unsubscribe(
        self,
        event_type: Type[T],
        handler: Callable[[T], None],
    ) -> None:
        """Remove a previously registered handler for ``event_type``."""
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            try:
                handlers.remove(handler)  # type: ignore[arg-type]
            except ValueError:
                logger.warning(
                    "Attempted to unsubscribe unknown handler %s from %s",
                    handler,
                    event_type.__name__,
                )

    # ── Publishing ────────────────────────────────────────────────────────────

    def publish(self, event: BaseEvent) -> None:
        """
        Publish ``event`` synchronously to all registered handlers.

        Handlers are called in registration order on the **calling thread**.
        Any exception raised by a handler is caught and logged; it does not
        prevent remaining handlers from being called.
        """
        event_type = type(event)
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.exception(
                    "Handler %s raised an exception processing %s: %s",
                    handler,
                    event_type.__name__,
                    exc,
                )

    def publish_async(self, event: BaseEvent) -> None:
        """
        Enqueue ``event`` for asynchronous delivery on the UI thread.

        The UI thread must call ``drain_async_queue()`` on each render cycle.
        This method is non-blocking and safe to call from the camera thread.
        """
        self._async_queue.put_nowait(event)

    def drain_async_queue(self, max_events: int = 32) -> None:
        """
        Dispatch up to ``max_events`` queued async events.

        Intended to be called from the UI event loop (e.g., Tkinter ``after``
        callback or Qt timer).
        """
        processed = 0
        while processed < max_events:
            try:
                event = self._async_queue.get_nowait()
            except queue.Empty:
                break
            self.publish(event)
            processed += 1

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def subscriber_count(self, event_type: Type[BaseEvent]) -> int:
        """Return the number of handlers registered for ``event_type``."""
        with self._lock:
            return len(self._handlers.get(event_type, []))

    def clear(self) -> None:
        """Remove all subscriptions. Intended for use in tests only."""
        with self._lock:
            self._handlers.clear()
        logger.debug("EventBus cleared (all subscriptions removed).")
