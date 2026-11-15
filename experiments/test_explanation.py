"""Manual experiment for the Phase 3 explanation chain."""

import sys

from chains.explanation_chain import generate_explanation
from schemas import TopicExplanation


sys.stdout.reconfigure(encoding="utf-8")

result = generate_explanation("Runnables in LangChain", "Intermediate")

if not isinstance(result, TopicExplanation):
    raise TypeError("The chain did not return a TopicExplanation.")

print("Topic:", result.topic)
print("Learning level:", result.learning_level)
print("\nIntroduction:\n", result.introduction)
print("\nDefinition:\n", result.definition)
print("\nHow it works:\n", result.how_it_works)
print("\nKey concepts:", ", ".join(result.key_concepts))
print("\nPractical examples:", *result.practical_examples, sep="\n- ")
print("\nAdvantages:", *result.advantages, sep="\n- ")
print("\nDisadvantages:", *result.disadvantages, sep="\n- ")
print("\nApplications:", *result.real_world_applications, sep="\n- ")
print("\nCommon mistakes:", *result.common_mistakes, sep="\n- ")
print("\nSummary:\n", result.summary)
