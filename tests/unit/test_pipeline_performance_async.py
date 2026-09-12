"""
Unit tests for Phase 14.6: Real-time Performance & Decoupled Asynchronous Frame Pipeline.
Verifies LatestFrameBuffer, AsyncCameraCapture, FrameTiming, latest-frame-wins semantics,
zero stale frame queue accumulation, and lifecycle thread safety.
"""

import time
import unittest
from unittest.mock import MagicMock

import numpy as np

from camera.frame_buffer import AsyncCameraCapture, FrameTiming, LatestFrameBuffer
from core.models import Frame


class TestPipelinePerformanceAsync(unittest.TestCase):
    def setUp(self):
        self.dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)

    def _make_frame(self, seq_id: int, capture_ts: float = 0.0) -> Frame:
        return Frame(
            image=self.dummy_image,
            timestamp=time.time(),
            seq_id=seq_id,
            width=640,
            height=480,
            capture_timestamp=capture_ts or time.monotonic(),
        )

    def test_01_frame_timing_latency_calculations(self):
        """FrameTiming accurately calculates capture-to-processing, duration, and end-to-end latency."""
        t0 = 100.0
        t1 = 100.005   # 5 ms capture-to-proc latency
        t2 = 100.025   # 20 ms processing duration (25 ms total e2e)

        timing = FrameTiming(
            frame_seq=1,
            capture_timestamp=t0,
            proc_start_timestamp=t1,
            proc_end_timestamp=t2,
            inference_time_ms=18.5,
        )

        self.assertAlmostEqual(timing.capture_to_proc_latency_ms, 5.0, delta=0.01)
        self.assertAlmostEqual(timing.processing_duration_ms, 20.0, delta=0.01)
        self.assertAlmostEqual(timing.end_to_end_latency_ms, 25.0, delta=0.01)
        self.assertEqual(timing.inference_time_ms, 18.5)

    def test_02_latest_frame_buffer_single_slot_get_put(self):
        """LatestFrameBuffer stores newest frame and clears new flag on get()."""
        buf = LatestFrameBuffer()
        f1 = self._make_frame(seq_id=1)

        buf.put(f1)
        self.assertEqual(buf.captured_count, 1)
        self.assertEqual(buf.dropped_count, 0)

        retrieved = buf.get(timeout=0.1)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.seq_id, 1)
        self.assertEqual(buf.consumed_count, 1)

        # Second get should timeout since frame was already consumed
        retrieved2 = buf.get(timeout=0.01)
        self.assertIsNone(retrieved2)

    def test_03_latest_frame_wins_drops_stale_frames(self):
        """When producer produces multiple frames before consumer reads, stale frames are discarded."""
        buf = LatestFrameBuffer()

        f1 = self._make_frame(seq_id=1)
        f2 = self._make_frame(seq_id=2)
        f3 = self._make_frame(seq_id=3)
        f4 = self._make_frame(seq_id=4)

        buf.put(f1)
        buf.put(f2)
        buf.put(f3)
        buf.put(f4)

        self.assertEqual(buf.captured_count, 4)
        self.assertEqual(buf.dropped_count, 3)  # 3 stale frames dropped

        # Consumer should receive newest frame 4 immediately
        retrieved = buf.get(timeout=0.1)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.seq_id, 4)
        self.assertEqual(buf.consumed_count, 1)

    def test_04_buffer_stop_unblocks_waiting_consumer(self):
        """Calling stop() on LatestFrameBuffer immediately unblocks any waiting consumer thread."""
        buf = LatestFrameBuffer()

        t_start = time.monotonic()
        # In a separate thread, stop buffer after 0.05s
        import threading
        t = threading.Timer(0.05, buf.stop)
        t.start()

        retrieved = buf.get(timeout=2.0)
        t_elapsed = time.monotonic() - t_start

        self.assertIsNone(retrieved)
        self.assertLess(t_elapsed, 0.5)

    def test_05_buffer_reset_clears_metrics(self):
        """LatestFrameBuffer reset() clears all counters and frames."""
        buf = LatestFrameBuffer()
        buf.put(self._make_frame(seq_id=1))
        buf.put(self._make_frame(seq_id=2))

        self.assertEqual(buf.captured_count, 2)
        buf.reset()

        self.assertEqual(buf.captured_count, 0)
        self.assertEqual(buf.dropped_count, 0)
        self.assertEqual(buf.consumed_count, 0)
        self.assertIsNone(buf.get(timeout=0.01))

    def test_06_async_camera_capture_lifecycle(self):
        """AsyncCameraCapture starts dedicated thread, reads frames, and stops cleanly."""
        mock_camera = MagicMock()
        mock_camera.fps = 30.0
        frame_counter = [0]

        def fake_read():
            frame_counter[0] += 1
            time.sleep(0.005)
            return self._make_frame(seq_id=frame_counter[0])

        mock_camera.read.side_effect = fake_read

        async_cap = AsyncCameraCapture(camera=mock_camera)
        async_cap.start()
        self.assertTrue(async_cap.is_running)

        # Allow capture thread to run for 50ms
        time.sleep(0.05)

        # Consumer pulls latest frame
        f = async_cap.get_latest_frame(timeout=0.1)
        self.assertIsNotNone(f)
        self.assertGreater(f.seq_id, 0)

        async_cap.stop()
        self.assertFalse(async_cap.is_running)
        self.assertGreater(mock_camera.read.call_count, 1)

    def test_07_zero_stale_frame_latency_under_slow_consumer(self):
        """When consumer spends 50ms processing, next frame read has low capture-to-process latency."""
        mock_camera = MagicMock()
        mock_camera.fps = 60.0
        seq = [0]

        def fake_read():
            seq[0] += 1
            time.sleep(0.005)
            return self._make_frame(seq_id=seq[0], capture_ts=time.monotonic())

        mock_camera.read.side_effect = fake_read

        async_cap = AsyncCameraCapture(camera=mock_camera)
        async_cap.start()

        # Simulate slow consumer: sleep 60ms between reads
        latencies = []
        for _ in range(5):
            time.sleep(0.03)  # simulate slow worker
            frame = async_cap.get_latest_frame(timeout=0.1)
            if frame:
                cap_to_proc = (time.monotonic() - frame.capture_timestamp) * 1000.0
                latencies.append(cap_to_proc)

        async_cap.stop()

        self.assertGreater(len(latencies), 2)
        # Latency of the newest available frame should remain under 25ms rather than accumulating
        for lat in latencies:
            self.assertLess(lat, 25.0)


if __name__ == "__main__":
    unittest.main()
