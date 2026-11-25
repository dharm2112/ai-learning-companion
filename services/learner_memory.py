"""Learner Memory Manager — semantic retrieval via ChromaDB + HuggingFace embeddings.

Responsibilities
----------------
1. After a learning session completes, embed a topic summary and store it in
   ChromaDB (tagged with user_id so isolation is enforced).
2. When a new topic is started, retrieve the k most semantically relevant
   past summaries for the same user.
3. Never return memories belonging to a different user.

Storage
-------
- ChromaDB (embedded) stores vector embeddings in CHROMA_PATH.
- Embeddings are computed locally by HuggingFace sentence-transformers.
- The ``HUGGINGFACEHUB_API_TOKEN`` env var authenticates gated model downloads.
"""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from config import get_chroma_path, get_embedding_model, get_huggingface_token


# ---------------------------------------------------------------------------
# Embedding model (cached — loaded once per process)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_embeddings() -> HuggingFaceEmbeddings:
    """Load the HuggingFace embedding model once and cache it."""
    token = get_huggingface_token()
    if token:
        os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", token)

    return HuggingFaceEmbeddings(
        model_name=get_embedding_model(),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# ---------------------------------------------------------------------------
# ChromaDB collection
# ---------------------------------------------------------------------------

_COLLECTION_NAME = "learner_memories"


def _get_vector_store() -> Chroma:
    """Return (or create) the ChromaDB collection backed by local disk."""
    return Chroma(
        collection_name=_COLLECTION_NAME,
        embedding_function=_get_embeddings(),
        persist_directory=get_chroma_path(),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_topic_memory(
    user_uuid: str,
    topic_name: str,
    summary_text: str,
    memory_type: str = "topic_summary",
) -> None:
    """Embed and store a topic summary for a specific user.

    Parameters
    ----------
    user_uuid:
        The UUID string of the learner (from ``user_identity.get_current_user_uuid()``).
    topic_name:
        Human-readable topic name, stored as metadata.
    summary_text:
        The text to embed (e.g. the explanation summary + key concepts).
    memory_type:
        "topic_summary" or "cross_topic" — stored as filterable metadata.
    """
    if not summary_text.strip():
        return

    doc = Document(
        page_content=summary_text,
        metadata={
            "user_uuid": user_uuid,
            "topic_name": topic_name,
            "memory_type": memory_type,
        },
    )
    store = _get_vector_store()
    store.add_documents([doc])


def retrieve_relevant_memories(
    user_uuid: str,
    new_topic: str,
    k: int = 3,
) -> list[dict]:
    """Retrieve the k most relevant past topic summaries for a user.

    Parameters
    ----------
    user_uuid:
        Filters results to this user only — prevents cross-user leakage.
    new_topic:
        The query text (new topic being started).
    k:
        Maximum number of memories to return.

    Returns
    -------
    list[dict] with keys: topic_name, content, memory_type
    """
    store = _get_vector_store()

    # Safety: always filter by user_uuid so one user cannot see another's data.
    results = store.similarity_search(
        query=new_topic,
        k=k,
        filter={"user_uuid": user_uuid},
    )

    memories = []
    for doc in results:
        # Skip if the memory is about the same topic (not cross-topic knowledge)
        if doc.metadata.get("topic_name", "").lower() == new_topic.strip().lower():
            continue
        memories.append(
            {
                "topic_name": doc.metadata.get("topic_name", ""),
                "content": doc.page_content,
                "memory_type": doc.metadata.get("memory_type", "topic_summary"),
            }
        )

    return memories


def build_memory_context(memories: list[dict]) -> str:
    """Format retrieved memories into a compact LLM-ready context string."""
    if not memories:
        return ""

    lines = ["The learner has previously studied these related topics:"]
    for mem in memories:
        topic = mem.get("topic_name", "Unknown")
        content = mem.get("content", "").strip()
        lines.append(f"\n### From: {topic}\n{content}")

    return "\n".join(lines)
