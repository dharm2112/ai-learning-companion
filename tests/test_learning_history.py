"""Unit tests for the LearningHistoryManager service.

Uses an in-memory SQLite database — no files written, no network calls.
Patches get_session() so every call uses the in-memory engine.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.database import Base
from db.models import ConceptProgress, LearningSession, QuizAnswer, QuizAttempt, Topic, User
from schemas.memory import LearnerProfile
from services.learning_history import (
    complete_session,
    get_learner_profile,
    get_mastered_concepts_for_topic,
    get_or_create_topic,
    get_recent_incorrect_questions,
    get_weak_concepts_for_topic,
    save_quiz_attempt,
    start_session,
    update_concept_progress,
)


# ---------------------------------------------------------------------------
# In-memory test database fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_session_factory():
    """Create an isolated in-memory SQLite engine for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # Must import models so the metadata is populated before create_all.
    import db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return factory


@pytest.fixture()
def db(in_memory_session_factory):
    """Return a patched get_session context manager using in-memory SQLite."""

    factory = in_memory_session_factory

    @contextmanager
    def _fake_get_session() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # We patch at the module level where get_session is *imported* from.
    targets = [
        "services.learning_history.get_session",
    ]
    with patch(targets[0], _fake_get_session):
        yield factory


@pytest.fixture()
def user_id(db) -> int:
    """Create a test user and return their DB primary key."""
    factory = db
    session = factory()
    user = User(user_uuid="test-uuid-1234")
    session.add(user)
    session.commit()
    uid = user.id
    session.close()
    return uid


# ---------------------------------------------------------------------------
# get_or_create_topic
# ---------------------------------------------------------------------------


class TestGetOrCreateTopic:
    def test_creates_topic_on_first_call(self, db, user_id):
        factory = db
        session = factory()
        topic = get_or_create_topic(session, "LangChain")
        session.commit()
        assert topic.id is not None
        assert topic.normalized_name == "langchain"
        session.close()

    def test_returns_same_row_on_duplicate(self, db, user_id):
        factory = db
        session = factory()
        t1 = get_or_create_topic(session, "LangChain")
        session.commit()
        t2 = get_or_create_topic(session, "LANGCHAIN")  # different case
        session.commit()
        assert t1.id == t2.id
        session.close()


# ---------------------------------------------------------------------------
# start_session / complete_session
# ---------------------------------------------------------------------------


class TestSessionLifecycle:
    def test_start_session_returns_int(self, db, user_id):
        session_id = start_session(user_id, "Python", "learn_first", "Beginner")
        assert isinstance(session_id, int)
        assert session_id > 0

    def test_complete_session_sets_flags(self, db, user_id):
        session_id = start_session(user_id, "Python", "learn_first", "Beginner")
        complete_session(session_id)

        factory = db
        session = factory()
        ls = session.get(LearningSession, session_id)
        assert ls.is_complete is True
        assert ls.completed_at is not None
        session.close()


# ---------------------------------------------------------------------------
# save_quiz_attempt
# ---------------------------------------------------------------------------

_SAMPLE_RESULTS = [
    {
        "concept_tested": "Retrievers",
        "question_text": "What is a retriever?",
        "question_type": "MCQ",
        "user_answer": "Wrong",
        "correct_answer": "A document fetcher",
        "is_correct": False,
        "explanation": "Retrievers fetch documents.",
    },
    {
        "concept_tested": "Messages",
        "question_text": "What is HumanMessage?",
        "question_type": "MCQ",
        "user_answer": "Human turn",
        "correct_answer": "Human turn",
        "is_correct": True,
        "explanation": "HumanMessage represents the user's turn.",
    },
]


class TestSaveQuizAttempt:
    def test_saves_attempt_and_answers(self, db, user_id):
        session_id = start_session(user_id, "LangChain", "learn_first", "Beginner")
        attempt_id = save_quiz_attempt(session_id, "initial", _SAMPLE_RESULTS, 50.0)

        factory = db
        session = factory()
        attempt = session.get(QuizAttempt, attempt_id)
        assert attempt.total_questions == 2
        assert attempt.correct_answers == 1
        assert attempt.score_percentage == 50.0
        answers = session.query(QuizAnswer).filter_by(attempt_id=attempt_id).all()
        assert len(answers) == 2
        session.close()

    def test_correct_count_matches_results(self, db, user_id):
        session_id = start_session(user_id, "Python", "test_first", "Intermediate")
        all_correct = [
            {**r, "is_correct": True, "user_answer": r["correct_answer"]}
            for r in _SAMPLE_RESULTS
        ]
        attempt_id = save_quiz_attempt(session_id, "follow_up", all_correct, 100.0)

        factory = db
        session = factory()
        attempt = session.get(QuizAttempt, attempt_id)
        assert attempt.correct_answers == 2
        session.close()


# ---------------------------------------------------------------------------
# update_concept_progress
# ---------------------------------------------------------------------------


class TestUpdateConceptProgress:
    def test_creates_progress_rows(self, db, user_id):
        session_id = start_session(user_id, "LangChain", "learn_first", "Beginner")
        save_quiz_attempt(session_id, "initial", _SAMPLE_RESULTS, 50.0)
        update_concept_progress(user_id, "LangChain", _SAMPLE_RESULTS)

        factory = db
        session = factory()
        rows = session.query(ConceptProgress).filter_by(user_id=user_id).all()
        concept_names = {row.concept_name for row in rows}
        assert "Retrievers" in concept_names
        assert "Messages" in concept_names
        session.close()

    def test_weak_concept_marked_correctly(self, db, user_id):
        session_id = start_session(user_id, "LangChain", "learn_first", "Beginner")
        three_wrong = [
            {**_SAMPLE_RESULTS[0], "is_correct": False},
            {**_SAMPLE_RESULTS[0], "is_correct": False},
            {**_SAMPLE_RESULTS[0], "is_correct": False},
        ]
        save_quiz_attempt(session_id, "initial", three_wrong, 0.0)
        update_concept_progress(user_id, "LangChain", three_wrong)

        factory = db
        session = factory()
        row = session.query(ConceptProgress).filter_by(
            user_id=user_id, concept_name="Retrievers"
        ).first()
        assert row.status == "weak"
        session.close()

    def test_mastered_concept_marked_correctly(self, db, user_id):
        session_id = start_session(user_id, "LangChain", "learn_first", "Beginner")
        five_correct = [
            {**_SAMPLE_RESULTS[1], "is_correct": True},
            {**_SAMPLE_RESULTS[1], "is_correct": True},
            {**_SAMPLE_RESULTS[1], "is_correct": True},
            {**_SAMPLE_RESULTS[1], "is_correct": True},
            {**_SAMPLE_RESULTS[1], "is_correct": True},
        ]
        save_quiz_attempt(session_id, "initial", five_correct, 100.0)
        update_concept_progress(user_id, "LangChain", five_correct)

        factory = db
        session = factory()
        row = session.query(ConceptProgress).filter_by(
            user_id=user_id, concept_name="Messages"
        ).first()
        assert row.status == "mastered"
        session.close()


# ---------------------------------------------------------------------------
# get_learner_profile
# ---------------------------------------------------------------------------


class TestGetLearnerProfile:
    def test_returns_learner_profile_instance(self, db, user_id):
        profile = get_learner_profile(user_id)
        assert isinstance(profile, LearnerProfile)

    def test_topics_studied_populated(self, db, user_id):
        start_session(user_id, "Python", "learn_first", "Beginner")
        start_session(user_id, "LangChain", "learn_first", "Intermediate")
        profile = get_learner_profile(user_id)
        names = [t.lower() for t in profile.topics_studied]
        assert "python" in names
        assert "langchain" in names

    def test_nonexistent_user_returns_empty_profile(self, db):
        profile = get_learner_profile(99999)
        assert profile.user_id == "99999"
        assert profile.topics_studied == []


# ---------------------------------------------------------------------------
# get_weak / mastered concepts for topic
# ---------------------------------------------------------------------------


class TestConceptQueries:
    def test_get_weak_concepts_for_topic(self, db, user_id):
        session_id = start_session(user_id, "LangChain", "learn_first", "Beginner")
        save_quiz_attempt(session_id, "initial", _SAMPLE_RESULTS, 50.0)
        update_concept_progress(user_id, "LangChain", _SAMPLE_RESULTS * 3)  # more wrong answers
        weak = get_weak_concepts_for_topic(user_id, "LangChain")
        # Retrievers is wrong; Messages is correct — Retrievers should be weak
        assert "Retrievers" in weak

    def test_unknown_topic_returns_empty(self, db, user_id):
        result = get_weak_concepts_for_topic(user_id, "NonExistentTopic")
        assert result == []

    def test_get_recent_incorrect_questions(self, db, user_id):
        session_id = start_session(user_id, "LangChain", "learn_first", "Beginner")
        save_quiz_attempt(session_id, "initial", _SAMPLE_RESULTS, 50.0)
        incorrect = get_recent_incorrect_questions(user_id, "LangChain", limit=5)
        assert len(incorrect) == 1
        assert incorrect[0]["concept_name"] == "Retrievers"
