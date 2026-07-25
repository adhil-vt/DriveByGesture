"""
tests.unit.test_event_bus
==========================
Unit tests for EventBus — the most critical shared infrastructure.
"""

from __future__ import annotations

import threading
from typing import List

import pytest

from core.event_bus import EventBus
from core.events import BaseEvent, ErrorEvent, FrameCapturedEvent


class TestEventBusSubscription:

    def test_subscribe_and_publish(self, event_bus: EventBus):
        """A subscribed handler is called when its event type is published."""
        received: List[BaseEvent] = []
        event_bus.subscribe(ErrorEvent, lambda e: received.append(e))

        evt = ErrorEvent(source="test", user_message="hello")
        event_bus.publish(evt)

        assert len(received) == 1
        assert received[0] is evt

    def test_handler_not_called_for_wrong_type(self, event_bus: EventBus):
        """A handler subscribed to ErrorEvent must NOT fire for other event types."""
        received: List[BaseEvent] = []
        event_bus.subscribe(ErrorEvent, lambda e: received.append(e))

        # Publish a different event type
        event_bus.publish(BaseEvent(source="test"))

        assert received == []

    def test_multiple_handlers_all_called(self, event_bus: EventBus):
        """All handlers registered for the same event type are called."""
        results: List[int] = []
        event_bus.subscribe(ErrorEvent, lambda e: results.append(1))
        event_bus.subscribe(ErrorEvent, lambda e: results.append(2))
        event_bus.subscribe(ErrorEvent, lambda e: results.append(3))

        event_bus.publish(ErrorEvent(source="test"))

        assert results == [1, 2, 3]

    def test_unsubscribe_removes_handler(self, event_bus: EventBus):
        """Unsubscribed handler is not called on subsequent publishes."""
        received: List[int] = []
        handler = lambda e: received.append(1)  # noqa: E731
        event_bus.subscribe(ErrorEvent, handler)
        event_bus.unsubscribe(ErrorEvent, handler)

        event_bus.publish(ErrorEvent(source="test"))

        assert received == []

    def test_handler_exception_does_not_stop_other_handlers(self, event_bus: EventBus):
        """An exception in one handler must not prevent other handlers from running."""
        second_called: List[bool] = []

        def bad_handler(e):
            raise RuntimeError("intentional test error")

        def good_handler(e):
            second_called.append(True)

        event_bus.subscribe(ErrorEvent, bad_handler)
        event_bus.subscribe(ErrorEvent, good_handler)

        event_bus.publish(ErrorEvent(source="test"))

        assert second_called == [True]

    def test_clear_removes_all_subscriptions(self, event_bus: EventBus):
        """clear() must reset the bus to empty state."""
        received: List[BaseEvent] = []
        event_bus.subscribe(ErrorEvent, lambda e: received.append(e))
        event_bus.clear()

        event_bus.publish(ErrorEvent(source="test"))

        assert received == []


class TestEventBusAsync:

    def test_publish_async_queues_event(self, event_bus: EventBus):
        """publish_async() queues the event; drain_async_queue() delivers it."""
        received: List[BaseEvent] = []
        event_bus.subscribe(ErrorEvent, lambda e: received.append(e))

        event_bus.publish_async(ErrorEvent(source="test"))
        assert received == [], "Should not be delivered before drain."

        event_bus.drain_async_queue()
        assert len(received) == 1


class TestEventBusThreadSafety:

    def test_concurrent_publish_does_not_raise(self, event_bus: EventBus):
        """Publishing from multiple threads concurrently must not raise."""
        received: List[int] = []
        lock = threading.Lock()

        def handler(e):
            with lock:
                received.append(1)

        event_bus.subscribe(ErrorEvent, handler)

        threads = [
            threading.Thread(target=lambda: event_bus.publish(ErrorEvent(source="t")))
            for _ in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(received) == 20
