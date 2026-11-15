"""Prompt used to create personalized learning recommendations."""

from langchain_core.prompts import ChatPromptTemplate


FURTHER_LEARNING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a personalized learning mentor.
Recommend only topics related to the current topic and the learner's weak concepts.
Use the learner's score and improvement suggestions to choose an appropriate level.

Provide:
- recommended_topics: related topics that strengthen weak concepts.
- advanced_topics: harder concepts that naturally follow the current topic.
- suggested_learning_order: a logical order with prerequisites first.
- custom_learning_suggestions: practical exercises or learning activities.

Avoid unrelated topics. Keep every recommendation specific and useful.""",
        ),
        (
            "human",
            "Topic: {topic}\n"
            "Learning level: {learning_level}\n"
            "Score: {score}\n"
            "Weak concepts: {weak_concepts}\n"
            "Improvement suggestions: {improvement_suggestions}",
        ),
    ]
)
