"""Pydantic schemas for learner memory, concept progress, and recommendations.

These are the validated transfer objects passed between the new services.
They do NOT replace the existing Quiz/Evaluation schemas; they extend them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Concept performance
# ---------------------------------------------------------------------------

ConceptStatus = Literal["weak", "learning", "mastered"]


class ConceptPerformanceSummary(BaseModel):
    """Snapshot of a user's performance on one concept — safe to serialise."""

    model_config = ConfigDict(extra="forbid")

    concept_name: str = Field(..., min_length=1)
    total_attempts: int = Field(..., ge=0)
    correct_attempts: int = Field(..., ge=0)
    weighted_score: float = Field(..., ge=0.0, le=1.0)
    status: ConceptStatus
    last_attempted: datetime | None = None

    @model_validator(mode="after")
    def correct_le_total(self) -> "ConceptPerformanceSummary":
        if self.correct_attempts > self.total_attempts:
            raise ValueError("correct_attempts cannot exceed total_attempts.")
        return self


# ---------------------------------------------------------------------------
# Learner profile
# ---------------------------------------------------------------------------


class LearnerProfile(BaseModel):
    """Aggregated snapshot of what a user has learned — used to build context."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., min_length=1)
    topics_studied: list[str] = Field(default_factory=list)
    weak_concepts: list[ConceptPerformanceSummary] = Field(default_factory=list)
    mastered_concepts: list[ConceptPerformanceSummary] = Field(default_factory=list)
    learning_concepts: list[ConceptPerformanceSummary] = Field(default_factory=list)
    total_sessions: int = Field(default=0, ge=0)
    total_quiz_attempts: int = Field(default=0, ge=0)
    last_active: datetime | None = None

    # --- helpers -----------------------------------------------------------

    @property
    def weak_concept_names(self) -> list[str]:
        return [c.concept_name for c in self.weak_concepts]

    @property
    def mastered_concept_names(self) -> list[str]:
        return [c.concept_name for c in self.mastered_concepts]

    def has_studied(self, topic: str) -> bool:
        return topic.strip().lower() in {t.lower() for t in self.topics_studied}


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

RecommendationType = Literal["revision", "practice", "next_topic"]


class Recommendation(BaseModel):
    """A single personalised recommendation for the learner."""

    model_config = ConfigDict(extra="forbid")

    rec_type: RecommendationType
    title: str = Field(..., min_length=1)
    reasoning: str = Field(..., min_length=1)
    action_label: str = Field(..., min_length=1)
    # Optional: topic or concept the recommendation targets.
    target: str = Field(default="")

    @property
    def emoji(self) -> str:
        return {"revision": "📖", "practice": "🎯", "next_topic": "🚀"}.get(
            self.rec_type, "💡"
        )


class RecommendationSet(BaseModel):
    """All recommendations generated after a learning session."""

    model_config = ConfigDict(extra="forbid")

    revision: list[Recommendation] = Field(default_factory=list)
    practice: list[Recommendation] = Field(default_factory=list)
    next_topic: list[Recommendation] = Field(default_factory=list)

    @property
    def all_recommendations(self) -> list[Recommendation]:
        return self.revision + self.practice + self.next_topic

    @property
    def is_empty(self) -> bool:
        return not self.all_recommendations
