"""Focused tests for Streamlit state and quiz-answer presentation safety."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from schemas import QuizQuestion, QuestionType


def test_public_question_excludes_backend_answer_fields() -> None:
    # Importing app.py is safe here because this test only checks its pure helper.
    import app

    question = QuizQuestion(
        question_id=1,
        question_text="What is LCEL?",
        question_type=QuestionType.MCQ,
        options=["A", "B"],
        correct_answer="A",
        explanation="A is correct.",
        concept_tested="LCEL",
        difficulty="Beginner",
    )

    public = app.public_question(question)

    assert set(public) == {
        "question_id",
        "question_text",
        "question_type",
        "options",
    }
    assert "correct_answer" not in public
    assert "explanation" not in public


def test_home_screen_renders_without_api_call() -> None:
    app_test = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()

    assert not app_test.exception
    assert any("Learn with clarity." in item.value for item in app_test.markdown)
    assert any(button.label == "Start Learning" for button in app_test.button)


def test_start_learning_opens_setup_screen() -> None:
    app_test = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()
    app_test.button[0].click().run()

    assert not app_test.exception
    assert any("Learning Setup" in title.value for title in app_test.title)


def test_empty_topic_is_rejected_without_backend_call() -> None:
    app_test = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()
    app_test.button[0].click().run()
    app_test.button[0].click().run()

    assert not app_test.exception
    assert any("Please enter a topic." in error.value for error in app_test.error)
