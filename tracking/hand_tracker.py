"""
gesturedrive.tracking.hand_tracker
====================================
IHandTracker abstraction and its MediaPipe 0.10+ HandLandmarker implementation.

Classes
-------
TrackingResult
    Full output of ``process_frame()``: annotated image + List[HandState].
MediaPipeHandTracker
    Production IHandTracker backed by ``mediapipe.tasks.vision.HandLandmarker``
    (MediaPipe 0.10+ Tasks API).
    Wraps the entire MediaPipe API surface; no other module imports mediapipe.

Model file
----------
MediaPipe 0.10+ requires an external ``hand_landmarker.task`` model bundle.
The tracker downloads it automatically on ``initialise()`` if it is not already
present in ``model_dir`` (default: ``models/`` relative to the project root).
The official download URL is defined in ``_MODEL_URL`` and the expected
filename in ``_MODEL_FILENAME``.

Configuration
-------------
All knobs (max_hands, min_detection_confidence, min_tracking_confidence)
are sourced from the injected ``TrackingConfig``.  No magic numbers here.
"""

from __future__ import annotations

import logging
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import cv2

from config.schema import TrackingConfig
from core.exceptions import TrackingError
from core.interfaces import IHandTracker
from core.models import Frame, Handedness
from tracking.hand_state import HandState
from tracking.landmark_normalizer import LandmarkNormalizer

logger = logging.getLogger(__name__)

# Alias for backward compatibility if imported elsewhere
DetectedHand = HandState

# ── Model download constants ───────────────────────────────────────────────────

_MODEL_FILENAME = "hand_landmarker.task"
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)
_DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


# ── Rich result returned by process_frame() ────────────────────────────────────

@dataclass
class TrackingResult:
    """
    Full output of ``MediaPipeHandTracker.process_frame()`` for one frame.

    Attributes
    ----------
    original_frame:
        The unmodified ``Frame`` received from the camera.
    annotated_image:
        A copy of the raw BGR image with landmarks, connections, IDs, and
        handedness labels drawn on it.  Shape: (H, W, 3), dtype uint8.
    hands:
        Ordered list of ``HandState`` per detected hand.  Empty when
        no hands are visible.
    """
    original_frame: Frame
    annotated_image: object                   # numpy.ndarray at runtime
    hands: List[HandState] = field(default_factory=list)

    @property
    def hand_count(self) -> int:
        """Number of hands detected in this frame."""
        return len(self.hands)


# ── Annotation constants ───────────────────────────────────────────────────────

_COLOR_LEFT_LM    = (0, 200, 255)    # amber
_COLOR_RIGHT_LM   = (0, 255, 100)    # green
_COLOR_LEFT_CONN  = (0, 140, 255)
_COLOR_RIGHT_CONN = (0, 200,  60)
_COLOR_LM_ID      = (255, 255, 255)
_COLOR_LABEL_BG   = (30, 30, 30)
_COLOR_LABEL_LEFT = (0, 200, 255)
_COLOR_LABEL_RIGHT= (0, 255, 100)
_COLOR_SHADOW     = (0, 0, 0)

_LM_RADIUS: int         = 5
_CONN_THICKNESS: int    = 2
_ID_SCALE: float        = 0.30
_ID_THICK: int          = 1
_LABEL_SCALE: float     = 0.65
_LABEL_THICK: int       = 2
_FONT = cv2.FONT_HERSHEY_SIMPLEX

# MediaPipe hand connection pairs — mirrors HandLandmarksConnections.HAND_CONNECTIONS
_HAND_CONNECTIONS: Tuple[Tuple[int, int], ...] = (
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index
    (0, 5), (1, 5), (5, 6), (6, 7), (7, 8),
    # Middle
    (9, 10), (10, 11), (11, 12),
    # Ring
    (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm
    (5, 9), (9, 13), (13, 17),
)


# ── MediaPipe Hand Tracker ─────────────────────────────────────────────────────

class MediaPipeHandTracker(IHandTracker):
    """
    IHandTracker implementation using MediaPipe 0.10+ HandLandmarker Tasks API.

    This class isolates the entire MediaPipe import surface. No other module
    in GestureDrive imports mediapipe.
    """

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
        model_path: Optional[Path] = None,
    ) -> None:
        self._max_num_hands = max_num_hands
        self._min_detection_confidence = min_detection_confidence
        self._min_tracking_confidence = min_tracking_confidence
        self._model_complexity = model_complexity
        self._model_path: Path = (
            model_path if model_path is not None
            else _DEFAULT_MODEL_DIR / _MODEL_FILENAME
        )

        self._landmarker = None        # mediapipe HandLandmarker — set in initialise()
        self._normalizer = LandmarkNormalizer()
        self._is_initialised: bool = False
        self._frame_timestamp_ms: int = 0   # monotonically increasing; required by VIDEO mode

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """
        Download the model if needed, then load and configure HandLandmarker.
        """
        if self._is_initialised:
            logger.warning(
                "MediaPipeHandTracker.initialise() called on an already-"
                "initialised tracker.  Call shutdown() first to re-initialise."
            )
            return

        logger.debug(
            "Initialising MediaPipe HandLandmarker: "
            "max_hands=%d, min_detection=%.2f, min_tracking=%.2f.",
            self._max_num_hands,
            self._min_detection_confidence,
            self._min_tracking_confidence,
        )

        self._ensure_model()

        try:
            import mediapipe as mp  # noqa: PLC0415

            BaseOptions = mp.tasks.BaseOptions
            HandLandmarker = mp.tasks.vision.HandLandmarker
            HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
            VisionRunningMode = mp.tasks.vision.RunningMode

            options = HandLandmarkerOptions(
                base_options=BaseOptions(
                    model_asset_path=str(self._model_path)
                ),
                running_mode=VisionRunningMode.VIDEO,
                num_hands=self._max_num_hands,
                min_hand_detection_confidence=self._min_detection_confidence,
                min_hand_presence_confidence=self._min_detection_confidence,
                min_tracking_confidence=self._min_tracking_confidence,
            )

            self._landmarker = HandLandmarker.create_from_options(options)

        except ImportError as exc:
            raise TrackingError(
                "mediapipe is not installed. Run: pip install mediapipe"
            ) from exc
        except Exception as exc:
            raise TrackingError(
                f"MediaPipe HandLandmarker failed to initialise: {exc}"
            ) from exc

        self._is_initialised = True
        self._frame_timestamp_ms = 0
        logger.info(
            "MediaPipe HandLandmarker initialised (max_hands=%d, model=%s).",
            self._max_num_hands,
            self._model_path.name,
        )

    def shutdown(self) -> None:
        """
        Close the HandLandmarker and free all resources.
        """
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception as exc:
                logger.warning(
                    "Exception while closing MediaPipe HandLandmarker: %s", exc
                )
            finally:
                self._landmarker = None
                self._is_initialised = False
                self._frame_timestamp_ms = 0

        logger.info("MediaPipe HandLandmarker shut down.")

    # ── IHandTracker ──────────────────────────────────────────────────────────

    def process(self, frame: Frame) -> List[HandState]:
        """
        Run HandLandmarker inference on ``frame`` and return a List[HandState].

        This is the ``IHandTracker`` contract method consumed by
        ``TrackingService`` in the full production pipeline.
        """
        return self.process_frame(frame).hands

    # ── Richer public API ──────────────────────────────────────────────────────

    def process_frame(self, frame: Frame) -> TrackingResult:
        """
        Run HandLandmarker inference and return a full ``TrackingResult``.
        """
        self._require_initialised()

        import mediapipe as mp  # noqa: PLC0415

        raw_image: object = frame.image  # numpy ndarray (BGR, H×W×3)

        # Convert BGR → RGB for MediaPipe.
        rgb = cv2.cvtColor(raw_image, cv2.COLOR_BGR2RGB)  # type: ignore[arg-type]

        # Wrap in a MediaPipe Image (SRGB = 3-channel uint8 RGB).
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_timestamp_ms += 33
        timestamp_ms = self._frame_timestamp_ms

        try:
            mp_result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception as exc:
            raise TrackingError(
                f"HandLandmarker.detect_for_video() failed on "
                f"frame {frame.seq_id}: {exc}"
            ) from exc

        annotated = raw_image.copy()  # type: ignore[attr-defined]

        detected_hand_states: List[HandState] = []

        has_landmarks = (
            mp_result.hand_landmarks
            and mp_result.handedness
            and len(mp_result.hand_landmarks) == len(mp_result.handedness)
        )

        if has_landmarks:
            for lm_list, cat_list in zip(
                mp_result.hand_landmarks, mp_result.handedness
            ):
                cat = cat_list[0]
                handedness = self._parse_handedness_category(cat)
                confidence = cat.score if cat.score is not None else 0.0

                try:
                    hand_state = self._normalizer.normalize(
                        raw_landmarks=lm_list,
                        handedness=handedness,
                        confidence=confidence,
                        timestamp=frame.timestamp,
                    )
                except ValueError as exc:
                    logger.warning(
                        "Landmark normalization failed (frame %d): %s "
                        "— skipping hand.",
                        frame.seq_id, exc,
                    )
                    continue

                detected_hand_states.append(hand_state)

                self._draw_hand(
                    image=annotated,
                    hand_state=hand_state,
                    frame_width=frame.width,
                    frame_height=frame.height,
                )
        else:
            logger.debug("No hands detected in frame %d.", frame.seq_id)

        if detected_hand_states:
            logger.debug(
                "Frame %d: %d hand(s) — %s.",
                frame.seq_id,
                len(detected_hand_states),
                ", ".join(
                    f"{hs.handedness.name}({hs.confidence:.2f})"
                    for hs in detected_hand_states
                ),
            )

        return TrackingResult(
            original_frame=frame,
            annotated_image=annotated,
            hands=detected_hand_states,
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_initialised(self) -> bool:
        """Return True if ``initialise()`` has been called successfully."""
        return self._is_initialised

    # ── Annotation ────────────────────────────────────────────────────────────

    def _draw_hand(
        self,
        image,
        hand_state: HandState,
        frame_width: int,
        frame_height: int,
    ) -> None:
        """
        Draw skeleton connections, landmark circles, IDs, and wrist label
        onto ``image`` in-place.
        """
        lm_color   = _COLOR_LEFT_LM   if hand_state.handedness == Handedness.LEFT else _COLOR_RIGHT_LM
        conn_color = _COLOR_LEFT_CONN if hand_state.handedness == Handedness.LEFT else _COLOR_RIGHT_CONN

        px_coords: List[Tuple[int, int]] = [
            (int(lm.x * frame_width), int(lm.y * frame_height))
            for lm in hand_state.landmarks
        ]

        # 1. Connections.
        for start_idx, end_idx in _HAND_CONNECTIONS:
            if start_idx < len(px_coords) and end_idx < len(px_coords):
                cv2.line(
                    image,
                    px_coords[start_idx],
                    px_coords[end_idx],
                    conn_color,
                    _CONN_THICKNESS,
                    cv2.LINE_AA,
                )

        # 2. Landmark circles.
        for px, py in px_coords:
            cv2.circle(image, (px, py), _LM_RADIUS + 1, _COLOR_SHADOW, -1)
            cv2.circle(image, (px, py), _LM_RADIUS, lm_color, -1)

        # 3. Landmark IDs.
        for idx, (px, py) in enumerate(px_coords):
            text = str(idx)
            cv2.putText(
                image, text, (px + 2, py - 3),
                _FONT, _ID_SCALE, _COLOR_SHADOW, _ID_THICK + 1, cv2.LINE_AA,
            )
            cv2.putText(
                image, text, (px + 1, py - 4),
                _FONT, _ID_SCALE, _COLOR_LM_ID, _ID_THICK, cv2.LINE_AA,
            )

        # 4. Handedness label near wrist.
        wrist_x, wrist_y = px_coords[0]
        label = f"{hand_state.handedness.name}  {hand_state.confidence:.0%}"
        label_fg = _COLOR_LABEL_LEFT if hand_state.handedness == Handedness.LEFT else _COLOR_LABEL_RIGHT

        (tw, th), _ = cv2.getTextSize(label, _FONT, _LABEL_SCALE, _LABEL_THICK)
        pad = 4
        cv2.rectangle(
            image,
            (wrist_x - pad, wrist_y - th - pad * 2),
            (wrist_x + tw + pad, wrist_y + pad),
            _COLOR_LABEL_BG, -1,
        )
        cv2.putText(
            image, label,
            (wrist_x, wrist_y - pad),
            _FONT, _LABEL_SCALE, label_fg, _LABEL_THICK, cv2.LINE_AA,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_handedness_category(category: object) -> Handedness:
        """
        Convert a MediaPipe 0.10+ ``Category`` object into ``Handedness``.
        """
        try:
            label: str = category.category_name or ""  # type: ignore[attr-defined]
        except AttributeError:
            return Handedness.UNKNOWN

        upper = label.strip().upper()
        if upper == "LEFT":
            return Handedness.LEFT
        if upper == "RIGHT":
            return Handedness.RIGHT

        logger.warning(
            "Unrecognized handedness category_name %r. Defaulting to UNKNOWN.",
            label,
        )
        return Handedness.UNKNOWN

    def _require_initialised(self) -> None:
        """Raise ``TrackingError`` if the tracker has not been initialised."""
        if not self._is_initialised or self._landmarker is None:
            raise TrackingError(
                "MediaPipeHandTracker is not initialised. "
                "Call initialise() before process() or process_frame()."
            )

    def _ensure_model(self) -> None:
        """
        Ensure ``self._model_path`` exists, downloading it if necessary.
        """
        if self._model_path.exists():
            logger.debug("Model file found: %s", self._model_path)
            return

        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Model file not found at %s. Downloading from %s …",
            self._model_path,
            _MODEL_URL,
        )

        try:
            urllib.request.urlretrieve(_MODEL_URL, self._model_path)
        except Exception as exc:
            if self._model_path.exists():
                self._model_path.unlink(missing_ok=True)
            raise TrackingError(
                f"Failed to download hand_landmarker.task from {_MODEL_URL}: {exc}. "
                f"Download it manually and place it at: {self._model_path}"
            ) from exc

        logger.info(
            "Model downloaded successfully (%d bytes).",
            self._model_path.stat().st_size,
        )

    # ── Context manager ────────────────────────────────────────────────────────

    def __enter__(self) -> "MediaPipeHandTracker":
        """Initialise the tracker when used as a context manager."""
        self.initialise()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Shut down the tracker on context manager exit."""
        self.shutdown()

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def from_config(
        cls,
        config: TrackingConfig,
        model_path: Optional[Path] = None,
    ) -> "MediaPipeHandTracker":
        """
        Construct a ``MediaPipeHandTracker`` from a ``TrackingConfig``.
        """
        return cls(
            max_num_hands=config.max_num_hands,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
            model_complexity=config.model_complexity,
            model_path=model_path,
        )
