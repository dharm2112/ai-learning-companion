"""Prompt used to grade one short answer."""

from langchain_core.prompts import ChatPromptTemplate


EVALUATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a fair technical instructor grading a short answer.
Judge conceptual correctness, not exact wording.
Mark is_correct true only when the answer includes the essential ideas.
Treat partially correct answers as false, but explain what is missing.
Do not reward unrelated or invented information.
Return is_correct, explanation, and concept_tested.""",
        ),
        (
            "human",
            "Question: {question}\n"
            "Expected answer: {expected_answer}\n"
            "User answer: {user_answer}\n"
            "Concept tested: {concept_tested}",
        ),
    ]
)
