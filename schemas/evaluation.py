"""Validated schema for deterministic and LLM-assisted quiz evaluation."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShortAnswerEvaluation(BaseModel):
    """Structured result returned when Groq grades a short answer."""

    model_config = ConfigDict(extra="forbid")

    is_correct: bool
    explanation: str = Field(..., min_length=1)
    concept_tested: str = Field(..., min_length=1)


class QuestionResult(BaseModel):
    """Evaluation result for one submitted answer."""

    model_config = ConfigDict(extra="forbid")

    question_id: int = Field(..., ge=1)
    user_answer: str = Field(default="")
    correct_answer: str = Field(..., min_length=1)
    is_correct: bool
    explanation: str = Field(..., min_length=1)
    concept_tested: str = Field(..., min_length=1)


class QuizEvaluation(BaseModel):
    """Aggregate quiz results with internally consistent counts and score."""

    model_config = ConfigDict(extra="forbid")

    total_questions: int = Field(..., ge=1)
    correct_answers: int = Field(..., ge=0)
    incorrect_answers: int = Field(..., ge=0)
    score_percentage: float = Field(..., ge=0, le=100)
    question_results: list[QuestionResult] = Field(..., min_length=1)
    weak_concepts: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_consistency(self) -> "QuizEvaluation":
        """Ensure aggregate fields agree with the individual question results."""

        if self.correct_answers + self.incorrect_answers != self.total_questions:
            raise ValueError("Correct and incorrect counts must equal total_questions.")
        if len(self.question_results) != self.total_questions:
            raise ValueError("question_results must contain total_questions results.")

        expected_score = (self.correct_answers / self.total_questions) * 100
        if abs(self.score_percentage - expected_score) > 0.01:
            raise ValueError("score_percentage must match the correct-answer percentage.")
        return self
