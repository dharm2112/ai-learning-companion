"""Validated schema for an AI-generated topic explanation."""

from pydantic import BaseModel, ConfigDict, Field


class TopicExplanation(BaseModel):
    """A complete explanation tailored to a learner's level."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(..., min_length=1, description="Topic being explained.")
    learning_level: str = Field(..., min_length=1, description="Learner's experience level.")
    introduction: str = Field(..., min_length=1, description="Plain-language introduction.")
    definition: str = Field(..., min_length=1, description="Clear definition of the topic.")
    why_it_is_important: str = Field(..., min_length=1, description="Why the topic matters.")
    how_it_works: str = Field(..., min_length=1, description="Explanation of the internal process.")
    key_concepts: list[str] = Field(..., min_length=1, description="Core concepts to remember.")
    practical_examples: list[str] = Field(..., min_length=1, description="Practical examples.")
    advantages: list[str] = Field(..., min_length=1, description="Important benefits.")
    disadvantages: list[str] = Field(..., min_length=1, description="Important limitations.")
    real_world_applications: list[str] = Field(
        ..., min_length=1, description="Real-world applications."
    )
    common_mistakes: list[str] = Field(..., min_length=1, description="Common learner mistakes.")
    summary: str = Field(..., min_length=1, description="Concise summary.")
