"""Manual experiment for the Phase 4 quiz chain."""

from chains.quiz_chain import generate_quiz
from schemas import Quiz


quiz = generate_quiz("Runnables in LangChain", "Intermediate", 6)

if not isinstance(quiz, Quiz):
    raise TypeError("The chain did not return a Quiz.")

print("Topic:", quiz.topic)
print("Learning level:", quiz.learning_level)
print("Question count:", len(quiz.questions))

for question in quiz.questions:
    print(f"\nQuestion {question.question_id} ({question.question_type.value})")
    print("Difficulty:", question.difficulty)
    print("Question:", question.question_text)
    print("Options:", question.options)
    print("Backend answer:", question.correct_answer)
    print("Explanation:", question.explanation)
