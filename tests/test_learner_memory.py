"""Tests for learner-memory filtering and prompt-context formatting."""

from unittest.mock import Mock, patch

from langchain_core.documents import Document

from services.learner_memory import build_memory_context, retrieve_relevant_memories


def test_memory_retrieval_always_filters_by_user_uuid() -> None:
    store = Mock()
    store.similarity_search.return_value = [
        Document(
            page_content="A useful summary.",
            metadata={"topic_name": "Vector databases", "memory_type": "topic_summary"},
        )
    ]

    with patch("services.learner_memory._get_vector_store", return_value=store):
        memories = retrieve_relevant_memories("learner-123", "Embeddings", k=2)

    store.similarity_search.assert_called_once_with(
        query="Embeddings",
        k=2,
        filter={"user_uuid": "learner-123"},
    )
    assert memories == [
        {
            "topic_name": "Vector databases",
            "content": "A useful summary.",
            "memory_type": "topic_summary",
        }
    ]


def test_same_topic_memory_is_excluded() -> None:
    store = Mock()
    store.similarity_search.return_value = [
        Document(
            page_content="Previous explanation.",
            metadata={"topic_name": "Python", "memory_type": "topic_summary"},
        )
    ]

    with patch("services.learner_memory._get_vector_store", return_value=store):
        memories = retrieve_relevant_memories("learner-123", " python ")

    assert memories == []


def test_memory_context_is_empty_when_no_memories_exist() -> None:
    assert build_memory_context([]) == ""
