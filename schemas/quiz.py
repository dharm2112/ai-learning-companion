"""Validated quiz schemas, including backend-only answer keys."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionType(str, Enum):
    """Supported question formats."""

    MCQ = "MCQ"
    TRUE_FALSE = "TRUE_FALSE"
    SHORT_ANSWER = "SHORT_ANSWER"


class QuizQuestion(BaseModel):
    """A quiz question with its answer key kept in the trusted backend model."""

    model_config = ConfigDict(extra="forbid")

    question_id: int = Field(..., ge=1, description="Unique positive question identifier.")
    question_text: str = Field(..., min_length=1, description="Question presented to the learner.")
    question_type: QuestionType
    options: list[str] = Field(default_factory=list, description="Choices for MCQ questions.")
    correct_answer: str = Field(..., min_length=1, description="Backend-only answer key.")
    explanation: str = Field(..., min_length=1, description="Explanation of the correct answer.")
    concept_tested: str = Field(..., min_length=1, description="Concept assessed by the question.")
    difficulty: str = Field(..., min_length=1, description="Question difficulty.")

    @model_validator(mode="after")
    def validate_options(self) -> "QuizQuestion":
        """Enforce the option shape required by each question type."""

        if self.question_type is QuestionType.MCQ and len(self.options) < 2:
            raise ValueError("MCQ questions must contain at least two options.")

        if self.question_type is QuestionType.TRUE_FALSE:
            normalized = {option.strip().lower() for option in self.options}
            if normalized != {"true", "false"}:
                raise ValueError("TRUE_FALSE questions must have exactly True and False options.")

        if self.question_type is QuestionType.SHORT_ANSWER and self.options:
            raise ValueError("SHORT_ANSWER questions must not contain options.")

        return self


class Quiz(BaseModel):
    """A quiz containing at least one uniquely identified question."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(..., min_length=1, description="Quiz topic.")
    learning_level: str = Field(..., min_length=1, description="Learner's experience level.")
    questions: list[QuizQuestion] = Field(..., min_length=1, description="Quiz questions.")

    @model_validator(mode="after")
    def validate_unique_question_ids(self) -> "Quiz":
        """Prevent ambiguous answer lookup during evaluation."""

        question_ids = [question.question_id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Question IDs must be unique within a quiz.")
        return self
