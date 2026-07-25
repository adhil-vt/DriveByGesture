"""
gesturedrive.analysis.hand_analyzer
====================================
HandAnalyzer service: batch coordinates finger analysis for all detected hands in a frame.

Responsibilities
----------------
- Accept List[HandState] / Sequence[HandState] from tracking.
- Delegate per-hand geometry analysis to an injected ``FingerAnalyzer``.
- Return List[HandAnalysis] with complete finger state results.
- Log finger state analysis results with confidence scores via standard logging system.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Sequence

from config.schema import AnalysisConfig
from analysis.finger_analyzer import FingerAnalyzer
from analysis.finger_state import HandAnalysis
from tracking.hand_state import HandState

logger = logging.getLogger(__name__)


class HandAnalyzer:
    """
    Coordinator service that analyzes a batch of detected hands.

    Parameters
    ----------
    finger_analyzer:
        Optional custom ``FingerAnalyzer`` instance for dependency injection.
        If ``None``, a default ``FingerAnalyzer`` is instantiated.
    config:
        Optional ``AnalysisConfig`` instance passed to default ``FingerAnalyzer``.
    """

    def __init__(
        self,
        finger_analyzer: Optional[FingerAnalyzer] = None,
        config: Optional[AnalysisConfig] = None,
    ) -> None:
        self._finger_analyzer = finger_analyzer or FingerAnalyzer(config=config)

    def analyze_hands(self, hand_states: Sequence[HandState]) -> List[HandAnalysis]:
        """
        Analyze a sequence of detected ``HandState`` objects.

        Parameters
        ----------
        hand_states:
            Sequence of ``HandState`` objects detected in a single frame.

        Returns
        -------
        List[HandAnalysis]
            Corresponding ``HandAnalysis`` results for each input hand.
        """
        if not hand_states:
            logger.debug("No hand states provided for analysis.")
            return []

        results: List[HandAnalysis] = []
        for state in hand_states:
            analysis = self._analyze_single_hand(state)
            results.append(analysis)

            logger.debug(
                "%s Hand\n"
                "Thumb  : %s (%.2f)\n"
                "Index  : %s (%.2f)\n"
                "Middle : %s (%.2f)\n"
                "Ring   : %s (%.2f)\n"
                "Pinky  : %s (%.2f)",
                analysis.hand_state.handedness.name.title(),
                analysis.thumb.position.name, analysis.thumb.confidence,
                analysis.index.position.name, analysis.index.confidence,
                analysis.middle.position.name, analysis.middle.confidence,
                analysis.ring.position.name, analysis.ring.confidence,
                analysis.pinky.position.name, analysis.pinky.confidence,
            )

        return results

    def _analyze_single_hand(self, hand_state: HandState) -> HandAnalysis:
        """
        Private helper to delegate single-hand analysis to FingerAnalyzer.
        """
        return self._finger_analyzer.analyze(hand_state)
