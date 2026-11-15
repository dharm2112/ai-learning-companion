"""Small experiment demonstrating LangChain's Pydantic structured output."""

from schemas import Quiz, TopicExplanation
from services.llm_service import get_chat_model


def main() -> None:
    """Invoke Groq with Pydantic schemas and print validated results."""

    llm = get_chat_model()
    topic = "Python functions"

    explanation_llm = llm.with_structured_output(TopicExplanation)
    explanation = explanation_llm.invoke(
        f"Explain {topic} for a beginner. Populate every required field with useful content."
    )
    if not isinstance(explanation, TopicExplanation):
        raise TypeError(f"Expected TopicExplanation, received {type(explanation).__name__}.")

    print("Structured TopicExplanation:")
    print(explanation)
    print(f"Topic: {explanation.topic}")
    print(f"Definition: {explanation.definition}")
    print(f"Key concepts: {', '.join(explanation.key_concepts)}")

    # json_schema is supported by the installed ChatGroq version for Quiz.
    quiz_llm = llm.with_structured_output(Quiz, method="json_schema")
    quiz = quiz_llm.invoke(
        f"Create one MCQ about {topic} for a beginner. "
        "Use question_id 1 and include at least two options."
    )
    if not isinstance(quiz, Quiz):
        raise TypeError(f"Expected Quiz, received {type(quiz).__name__}.")
    print("\nStructured Quiz:")
    print(quiz)


if __name__ == "__main__":
    main()
