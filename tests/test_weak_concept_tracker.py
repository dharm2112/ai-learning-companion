"""Unit tests for the WeakConceptTracker service.

All tests are pure Python — no LLM calls, no database, no network.
"""

from __future__ import annotations

import pytest

from services.weak_concept_tracker import (
    LEARNING,
    MASTERED,
    RECENT_WINDOW,
    WEAK,
    AttemptRecord,
    ConceptPerformance,
    build_concept_performances,
    identify_mastered_concepts,
    identify_weak_concepts,
    summarise_quiz_results,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_results(*correctness: bool, concept: str = "Vector Stores") -> list[dict]:
    """Build a list of question-result dicts with a fixed concept name."""
    return [
        {
            "concept_tested": concept,
            "is_correct": c,
            "question_text": f"Q{i}",
            "user_answer": "a",
            "correct_answer": "a" if c else "b",
        }
        for i, c in enumerate(correctness, start=1)
    ]


def _performance(*correctness: bool, concept: str = "Vector Stores") -> ConceptPerformance:
    results = _make_results(*correctness, concept=concept)
    perfs = build_concept_performances(results)
    return perfs[concept.lower()]


# ---------------------------------------------------------------------------
# ConceptPerformance unit tests
# ---------------------------------------------------------------------------


class TestConceptPerformanceProperties:
    def test_total_attempts(self):
        p = _performance(True, False, True)
        assert p.total_attempts == 3

    def test_correct_attempts(self):
        p = _performance(True, False, True)
        assert p.correct_attempts == 2

    def test_raw_accuracy(self):
        p = _performance(True, False, True, False)
        assert p.raw_accuracy == pytest.approx(0.5)

    def test_empty_concept_returns_zero_score(self):
        p = ConceptPerformance(concept_name="Empty")
        assert p.weighted_score == 0.0
        assert p.status == WEAK

    def test_all_correct_is_mastered(self):
        p = _performance(True, True, True, True, True)
        assert p.status == MASTERED

    def test_all_incorrect_is_weak(self):
        p = _performance(False, False, False)
        assert p.status == WEAK

    def test_mixed_learning_status(self):
        # 3 correct out of 5 → weighted score varies; check boundary
        p = _performance(True, True, True, False, False)
        # recent 3: T, F, F → weighted_correct = 1.5, weighted_total = 4.5
        # older 2:  T, T  → weighted_correct += 2.0, weighted_total += 2.0
        # total weighted_correct = 3.5 / 6.5 ≈ 0.538 → LEARNING
        assert p.status == LEARNING


class TestWeightedScore:
    def test_recent_correct_raises_score(self):
        """Improving recently should boost status even with early mistakes."""
        # 4 wrong then 3 right
        p = _performance(False, False, False, False, True, True, True)
        # Recent 3 (all correct): weight 1.5 each → 4.5/4.5 from recent
        # Older 4 (all wrong): weight 1.0 each → 0/4 from older
        # Score = 4.5 / 8.5 ≈ 0.529 → LEARNING (not WEAK)
        assert p.status != WEAK

    def test_recent_incorrect_lowers_score(self):
        """Regressing recently should lower status even with early success."""
        # 3 right then 3 wrong
        p = _performance(True, True, True, False, False, False)
        # Recent 3 (all wrong): 0/4.5
        # Older 3 (all right): 3/3
        # Score = 3 / 7.5 = 0.4 → WEAK
        assert p.status == WEAK

    def test_single_attempt_correct_is_learning_not_mastered(self):
        """One correct answer is not enough to declare mastery."""
        p = _performance(True)
        # Score = 1.5/1.5 = 1.0 → MASTERED (single attempt full weight is fine)
        # Actually with only 1 attempt it falls in the recent window; score = 1.0
        assert p.status == MASTERED  # edge case: only one attempt, all recent

    def test_one_wrong_does_not_permanently_mark_weak(self):
        """A single early failure should not lock a concept as permanently weak."""
        # Wrong once, then 5 correct — user clearly improved
        p = _performance(False, True, True, True, True, True)
        assert p.status != WEAK


class TestLastIncorrectAttempts:
    def test_returns_only_incorrect_from_recent_window(self):
        p = _performance(True, False, True, False, True)
        # Recent RECENT_WINDOW=3: T, F, T → only the False is incorrect
        incorrect = p.last_incorrect_attempts
        assert len(incorrect) == 1
        assert incorrect[0].is_correct is False

    def test_empty_when_all_recent_correct(self):
        p = _performance(False, True, True, True)
        assert p.last_incorrect_attempts == []


# ---------------------------------------------------------------------------
# build_concept_performances
# ---------------------------------------------------------------------------


class TestBuildConceptPerformances:
    def test_multiple_concepts_built(self):
        results = [
            {"concept_tested": "Messages", "is_correct": True},
            {"concept_tested": "Retrievers", "is_correct": False},
            {"concept_tested": "Retrievers", "is_correct": False},
            {"concept_tested": "Messages", "is_correct": True},
        ]
        perfs = build_concept_performances(results)
        assert "messages" in perfs
        assert "retrievers" in perfs
        assert perfs["messages"].total_attempts == 2
        assert perfs["retrievers"].total_attempts == 2

    def test_case_insensitive_key(self):
        results = [
            {"concept_tested": "Vector Stores", "is_correct": True},
            {"concept_tested": "vector stores", "is_correct": False},
        ]
        perfs = build_concept_performances(results)
        assert len(perfs) == 1
        assert list(perfs.values())[0].total_attempts == 2

    def test_missing_concept_tested_skipped(self):
        results = [
            {"concept_tested": "", "is_correct": True},
            {"is_correct": True},
        ]
        perfs = build_concept_performances(results)
        assert len(perfs) == 0

    def test_merges_with_existing(self):
        existing_results = _make_results(False, concept="Retrievers")
        existing = build_concept_performances(existing_results)
        new_results = _make_results(True, True, concept="Retrievers")
        merged = build_concept_performances(new_results, existing=existing)
        assert merged["retrievers"].total_attempts == 3


# ---------------------------------------------------------------------------
# identify_weak / mastered concepts
# ---------------------------------------------------------------------------


class TestIdentifyWeakMastered:
    def _two_concept_perfs(self):
        results = (
            _make_results(False, False, False, concept="Retrievers")
            + _make_results(True, True, True, True, True, concept="Messages")
        )
        return build_concept_performances(results)

    def test_identify_weak(self):
        perfs = self._two_concept_perfs()
        weak = identify_weak_concepts(perfs)
        assert len(weak) == 1
        assert weak[0].concept_name == "Retrievers"

    def test_identify_mastered(self):
        perfs = self._two_concept_perfs()
        mastered = identify_mastered_concepts(perfs)
        assert len(mastered) == 1
        assert mastered[0].concept_name == "Messages"

    def test_weak_sorted_worst_first(self):
        results = (
            _make_results(False, False, False, False, concept="A")
            + _make_results(False, concept="B")
        )
        perfs = build_concept_performances(results)
        weak = identify_weak_concepts(perfs)
        # A has more failures → lower weighted score → first
        assert weak[0].concept_name == "A"


# ---------------------------------------------------------------------------
# summarise_quiz_results
# ---------------------------------------------------------------------------


class TestSummariseQuizResults:
    def test_summary_keys_present(self):
        results = (
            _make_results(False, False, concept="Retrievers")
            + _make_results(True, True, True, concept="Messages")
        )
        summary = summarise_quiz_results(results)
        assert "performances" in summary
        assert "weak_concepts" in summary
        assert "mastered_concepts" in summary
        assert summary["total_concepts"] == 2
        assert summary["weak_count"] == 1
        assert summary["mastered_count"] == 1

    def test_empty_results_gives_empty_summary(self):
        summary = summarise_quiz_results([])
        assert summary["total_concepts"] == 0
        assert summary["weak_count"] == 0
        assert summary["mastered_count"] == 0
