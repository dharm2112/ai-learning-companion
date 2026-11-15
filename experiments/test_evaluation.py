"""Manual experiment for the Phase 6 quiz evaluation system."""

from chains.evaluation_chain import evaluate_quiz
from schemas import Quiz, QuizQuestion, QuestionType


quiz = Quiz(
    topic="LangChain",
    learning_level="Intermediate",
    questions=[
        QuizQuestion(
            question_id=1,
            question_text="What does LCEL use to compose runnables?",
            question_type=QuestionType.MCQ,
            options=["The pipe operator", "A database", "A web server", "A vector"],
            correct_answer="The pipe operator",
            explanation="The pipe operator composes runnables.",
            concept_tested="LCEL",
            difficulty="Beginner",
        ),
        QuizQuestion(
            question_id=2,
            question_text="RunnableParallel runs independent branches together.",
            question_type=QuestionType.TRUE_FALSE,
            options=["True", "False"],
            correct_answer="True",
            explanation="RunnableParallel runs independent branches concurrently.",
            concept_tested="RunnableParallel",
            difficulty="Intermediate",
        ),
        QuizQuestion(
            question_id=3,
            question_text="What does invoke do?",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="It executes a runnable with an input.",
            explanation="invoke executes a runnable.",
            concept_tested="invoke",
            difficulty="Beginner",
        ),
        QuizQuestion(
            question_id=4,
            question_text="A prompt can be part of a runnable sequence.",
            question_type=QuestionType.TRUE_FALSE,
            options=["True", "False"],
            correct_answer="True",
            explanation="Prompt templates can be runnable steps.",
            concept_tested="RunnableSequence",
            difficulty="Beginner",
        ),
        QuizQuestion(
            question_id=5,
            question_text="What does structured output provide?",
            question_type=QuestionType.MCQ,
            options=["Validated objects", "Only images", "A database", "A browser"],
            correct_answer="Validated objects",
            explanation="Structured output parses model output into a schema.",
            concept_tested="Structured output",
            difficulty="Intermediate",
        ),
        QuizQuestion(
            question_id=6,
            question_text="Why use Pydantic?",
            question_type=QuestionType.SHORT_ANSWER,
            correct_answer="It validates that data has the expected structure.",
            explanation="Pydantic validates typed data.",
            concept_tested="Pydantic",
            difficulty="Beginner",
        ),
    ],
)

answers = {
    1: "The pipe operator",
    2: "True",
    3: "It executes a runnable with an input.",
    4: "False",
    5: "Validated objects",
    6: "It checks the data structure.",
}

evaluation = evaluate_quiz(quiz, answers)

for result in evaluation.question_results:
    print(f"\nQuestion {result.question_id}")
    print("User answer:", result.user_answer)
    print("Correct:", result.is_correct)
    print("Explanation:", result.explanation)

print("\nCorrect answers:", evaluation.correct_answers)
print("Incorrect answers:", evaluation.incorrect_answers)
print("Total score:", evaluation.score_percentage)
print("Weak concepts:", evaluation.weak_concepts)
print("Improvement suggestions:", evaluation.improvement_suggestions)
