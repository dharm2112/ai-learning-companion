"""Prompt used to generate a validated quiz."""

from langchain_core.prompts import ChatPromptTemplate


QUIZ_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an experienced instructor and quiz creator.
Create an accurate quiz about the requested topic and learning level.
Do not invent specific facts, classes, methods, or APIs. Use current, established
terminology and avoid obsolete API claims. If a detail is uncertain, test a
broader concept instead of guessing. Do not write ambiguous questions.

Learning level instructions:
- Beginner: test fundamental understanding with simple definitions and basic concepts.
- Intermediate: test conceptual understanding with practical scenarios and code questions
  when relevant.
- Industry Level: test production understanding with engineering scenarios, architecture,
  trade-offs, and implementation decisions.

Use the requested question count exactly.
Use this practical distribution: prioritize MCQs, then distribute True/False and
Short Answer questions as evenly as possible. For six questions, create three MCQs,
two True/False questions, and one Short Answer question.
Before returning, count the questions and confirm the list contains exactly
{question_count} items with sequential question_id values from 1 through
{question_count}. Never return fewer or more questions.

Question rules:
- MCQ questions must have four options and exactly one correct answer.
- True/False questions must have the options True and False, with a correct answer
  of True or False.
- Short Answer questions must have no options and an expected answer of a few sentences.

Every question must include question_id, question_text, question_type, options,
correct_answer, explanation, concept_tested, and difficulty.""",
        ),
        (
            "human",
            "Topic: {topic}\nLearning level: {learning_level}\n"
            "Question count: {question_count}\nDistribution: {distribution}",
        ),
    ]
)
