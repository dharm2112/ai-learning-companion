"""Track concept-level performance and determine mastery status.

This module is intentionally stateless — it works on data passed to it
and returns results.  Persistence is handled by LearningHistoryManager.

Mastery thresholds
------------------
- mastered  : weighted score >= 0.80
- learning  : weighted score >= 0.50
- weak      : weighted score <  0.50

A concept is never permanently labelled "weak" after a single mistake.
The weighted rolling average gives recent attempts more influence so that
improvement is reflected quickly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

MASTERED = "mastered"
LEARNING = "learning"
WEAK     = "weak"

MASTERY_THRESHOLD = 0.80
LEARNING_THRESHOLD = 0.50

# How many recent attempts receive extra weight (1.5×) over older ones.
RECENT_WINDOW = 3


@dataclass(frozen=True)
class AttemptRecord:
    """A single attempt at a concept (one quiz question result)."""

    is_correct: bool
    question_text: str = ""
    user_answer: str = ""
    correct_answer: str = ""


@dataclass
class ConceptPerformance:
    """Aggregated performance for one concept across all attempts."""

    concept_name: str
    attempts: list[AttemptRecord] = field(default_factory=list)

    # --- computed on demand ------------------------------------------------

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    @property
    def correct_attempts(self) -> int:
        return sum(1 for a in self.attempts if a.is_correct)

    @property
    def raw_accuracy(self) -> float:
        """Simple correct / total — useful for display."""
        if not self.attempts:
            return 0.0
        return self.correct_attempts / self.total_attempts

    @property
    def weighted_score(self) -> float:
        """Recent attempts count 1.5×, older ones count 1.0×.

        Returns 0.0 when there are no attempts.
        """
        if not self.attempts:
            return 0.0

        total_weight = 0.0
        weighted_correct = 0.0

        for i, attempt in enumerate(self.attempts):
            # The last RECENT_WINDOW attempts are "recent".
            is_recent = i >= len(self.attempts) - RECENT_WINDOW
            weight = 1.5 if is_recent else 1.0
            total_weight += weight
            if attempt.is_correct:
                weighted_correct += weight

        return weighted_correct / total_weight

    @property
    def status(self) -> str:
        score = self.weighted_score
        if score >= MASTERY_THRESHOLD:
            return MASTERED
        if score >= LEARNING_THRESHOLD:
            return LEARNING
        return WEAK

    @property
    def last_incorrect_attempts(self) -> list[AttemptRecord]:
        """Return incorrect attempts from the most recent window, newest first."""
        recent = self.attempts[-RECENT_WINDOW:]
        return [a for a in reversed(recent) if not a.is_correct]


# ---------------------------------------------------------------------------
# Core tracker functions
# ---------------------------------------------------------------------------

def build_concept_performances(
    question_results: Sequence[dict],
    existing: dict[str, ConceptPerformance] | None = None,
) -> dict[str, ConceptPerformance]:
    """Build or update concept performances from a list of question result dicts.

    Parameters
    ----------
    question_results:
        Each dict must contain at minimum:
        ``concept_tested`` (str), ``is_correct`` (bool).
        Optional: ``question_text``, ``user_answer``, ``correct_answer``.
    existing:
        Previously accumulated ``ConceptPerformance`` objects to update.
        Pass ``None`` (default) to start fresh.

    Returns
    -------
    dict[str, ConceptPerformance]
        Keyed by normalised concept name (lowercase, stripped).
    """
    performances: dict[str, ConceptPerformance] = dict(existing or {})

    for result in question_results:
        raw_name: str = result.get("concept_tested", "").strip()
        if not raw_name:
            continue

        key = raw_name.lower()
        if key not in performances:
            performances[key] = ConceptPerformance(concept_name=raw_name)

        performances[key].attempts.append(
            AttemptRecord(
                is_correct=bool(result.get("is_correct", False)),
                question_text=result.get("question_text", ""),
                user_answer=str(result.get("user_answer", "")),
                correct_answer=str(result.get("correct_answer", "")),
            )
        )

    return performances


def identify_weak_concepts(
    performances: dict[str, ConceptPerformance],
) -> list[ConceptPerformance]:
    """Return concepts whose status is WEAK, sorted by weighted score (worst first)."""
    weak = [p for p in performances.values() if p.status == WEAK]
    return sorted(weak, key=lambda p: p.weighted_score)


def identify_mastered_concepts(
    performances: dict[str, ConceptPerformance],
) -> list[ConceptPerformance]:
    """Return concepts whose status is MASTERED, sorted by weighted score (best first)."""
    mastered = [p for p in performances.values() if p.status == MASTERED]
    return sorted(mastered, key=lambda p: p.weighted_score, reverse=True)


def summarise_quiz_results(
    question_results: Sequence[dict],
) -> dict:
    """One-shot helper: build performances and return a summary dict.

    Returns
    -------
    dict with keys:
        performances, weak_concepts, mastered_concepts,
        total_concepts, weak_count, mastered_count
    """
    performances = build_concept_performances(question_results)
    weak = identify_weak_concepts(performances)
    mastered = identify_mastered_concepts(performances)

    return {
        "performances": performances,
        "weak_concepts": weak,
        "mastered_concepts": mastered,
        "total_concepts": len(performances),
        "weak_count": len(weak),
        "mastered_count": len(mastered),
    }
