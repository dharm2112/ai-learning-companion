"""Manual experiment for the Phase 5 parallel chain."""

import sys

from chains.parallel_chain import generate_learning_material
from schemas import Quiz, TopicExplanation


sys.stdout.reconfigure(encoding="utf-8")

result = generate_learning_material("Runnables in LangChain", "Intermediate", 6)
explanation = result["explanation"]
quiz = result["quiz"]

print("Explanation type is correct:", isinstance(explanation, TopicExplanation))
print("Quiz type is correct:", isinstance(quiz, Quiz))
print("\nGenerated explanation:\n", explanation)
print("\nGenerated quiz:\n", quiz)
print("\nTotal questions:", len(quiz.questions))
