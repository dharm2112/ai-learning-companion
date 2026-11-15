"""Validated schema for further-learning recommendations."""

from pydantic import BaseModel, ConfigDict, Field


class FurtherLearning(BaseModel):
    """Recommendations for continuing a learner's study path."""

    model_config = ConfigDict(extra="forbid")

    recommended_topics: list[str] = Field(
        default_factory=list, description="Related topics suitable for the learner."
    )
    advanced_topics: list[str] = Field(
        default_factory=list, description="More advanced follow-up topics."
    )
    suggested_learning_order: list[str] = Field(
        default_factory=list, description="Recommended sequence of topics."
    )
    custom_learning_suggestions: list[str] = Field(
        default_factory=list, description="Suggestions for custom study."
    )
