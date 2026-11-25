"""Streamlit interface for the AI Learning Companion — Adaptive Edition."""

from datetime import datetime

import streamlit as st

from chains.evaluation_chain import evaluate_quiz
from chains.explanation_chain import generate_explanation, generate_contextual_explanation
from chains.learning_chain import (
    generate_custom_learning,
    generate_learning_recommendations,
)
from chains.parallel_chain import generate_learning_material
from chains.quiz_chain import generate_quiz, generate_adaptive_quiz
from db.migrations import run_migrations
from schemas import Quiz, QuizEvaluation, QuestionType, TopicExplanation
from services.adaptive_quiz import build_quiz_context
from services.learning_history import (
    complete_session,
    get_learner_profile,
    save_quiz_attempt,
    start_session,
    update_concept_progress,
    get_weak_concepts_for_topic,
)
from services.recommendation_engine import (
    generate_recommendations,
    format_recommendations_as_text,
)

# Run DB migrations on startup (no-op if tables already exist).
try:
    run_migrations()
except Exception:
    pass  # DB not available — degrade gracefully



st.set_page_config(
    page_title="AI Learning Companion",
    page_icon=":books:",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root { --primary: #6366f1; --ink: #e5e7eb; --muted: #a7b0c0; }
    .block-container { max-width: 1180px; padding: 2.5rem 3rem 5rem; }
    .hero { background: linear-gradient(135deg, #172554, #312e81);
            border: 1px solid #dbeafe; border-radius: 1.25rem;
            padding: 2.5rem; margin-bottom: 2rem; }
    .hero h1 { color: #ffffff; font-size: clamp(2rem, 5vw, 3.5rem);
               line-height: 1.05; margin: .25rem 0 1rem; }
    .hero p { color: #dbeafe; font-size: 1.08rem; max-width: 650px; }
    .eyebrow { color: #c7d2fe !important; font-size: .75rem !important;
               font-weight: 700; letter-spacing: .12em; }
    .feature-card, .content-card { background: #151a24; border: 1px solid #2b3445;
                                    border-radius: .9rem; padding: 1.25rem;
                                    margin: .5rem 0 1.25rem;
                                    box-shadow: 0 5px 18px rgba(15,23,42,.04); }
    .feature-card h3 { color: #c7d2fe; margin-top: 0; }
    .feature-card p { color: #cbd5e1; margin-bottom: 0; }
    [data-testid="stMetric"] { background: #151a24; border: 1px solid #334155;
                                border-radius: .9rem; padding: 1rem; min-height: 96px; }
    [data-testid="stMetricLabel"] { color: #a7b0c0 !important; }
    [data-testid="stMetricValue"] { color: #f8fafc !important; }
    .results-header { background: linear-gradient(135deg, #172554, #1e293b);
                      border: 1px solid #334155; border-radius: 1rem;
                      padding: 1.5rem 1.75rem; margin: 1rem 0 1.5rem; }
    .results-header h2 { color: #ffffff; margin: 0 0 .35rem; }
    .results-header p { color: #cbd5e1; margin: 0; }
    .section-heading { margin-top: 2rem; padding-bottom: .6rem;
                       border-bottom: 1px solid #334155; }
    .feedback-correct { border-left: 4px solid #22c55e; }
    .feedback-incorrect { border-left: 4px solid #f97316; }
    @media (max-width: 700px) {
        .block-container { padding: 1.25rem 1rem 3rem; }
        .hero { padding: 1.5rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state() -> None:
    """Create session values once so reruns do not lose progress."""

    defaults = {
        "page": "Home",
        "topic": "",
        "learning_level": "Beginner",
        "learning_path": "Learn + Test",
        "question_count": 6,
        "explanation": None,
        "quiz": None,
        "quiz_evaluation": None,
        "quiz_started": False,
        "confirm_submit": False,
        "current_question": 0,
        "answers": {},
        "recommendations": None,
        "custom_explanation": None,
        "history": [],
        # --- Adaptive Learning System additions ---
        "db_session_id": None,       # current LearningSession PK
        "db_user_id": None,          # User PK (set by user_identity service)
        "adaptive_recommendations": None,  # RecommendationSet
        "learner_profile": None,     # LearnerProfile (cached per session)
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialise persistent user identity (safe no-op if DB unavailable).
    if st.session_state.db_user_id is None:
        try:
            from services.user_identity import get_or_create_user
            st.session_state.db_user_id = get_or_create_user()
        except Exception:
            st.session_state.db_user_id = -1  # sentinel: DB unavailable


def show_error(message: str) -> None:
    """Show a safe error message without exposing provider internals."""

    st.error(message)


def reset_learning_session() -> None:
    """Clear the current learning material while keeping the app open."""

    st.session_state.topic = ""
    st.session_state.explanation = None
    st.session_state.quiz = None
    st.session_state.quiz_evaluation = None
    st.session_state.quiz_started = False
    st.session_state.confirm_submit = False
    st.session_state.current_question = 0
    st.session_state.answers = {}
    st.session_state.recommendations = None
    st.session_state.custom_explanation = None
    st.session_state.db_session_id = None
    st.session_state.adaptive_recommendations = None
    st.session_state.learner_profile = None
    st.session_state.page = "Learning Setup"


def public_question(question) -> dict:
    """Return only fields safe to show before quiz submission."""

    return {
        "question_id": question.question_id,
        "question_text": question.question_text,
        "question_type": question.question_type,
        "options": list(question.options),
    }


def display_explanation(explanation: TopicExplanation) -> None:
    """Display explanation fields without exposing quiz answer keys."""

    st.markdown('<div class="content-card">', unsafe_allow_html=True)
    st.subheader("Introduction")
    st.write(explanation.introduction)
    st.subheader("Definition")
    st.write(explanation.definition)
    st.subheader("Why It Is Important")
    st.write(explanation.why_it_is_important)
    st.subheader("How It Works")
    st.write(explanation.how_it_works)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Key Concepts", expanded=True):
        for item in explanation.key_concepts:
            st.markdown(f"- {item}")
    with st.expander("Practical Examples"):
        for item in explanation.practical_examples:
            st.markdown(f"- {item}")
    with st.expander("Advantages and Disadvantages"):
        st.markdown("**Advantages**")
        for item in explanation.advantages:
            st.markdown(f"- {item}")
        st.markdown("**Disadvantages**")
        for item in explanation.disadvantages:
            st.markdown(f"- {item}")
    with st.expander("Real-world Applications"):
        for item in explanation.real_world_applications:
            st.markdown(f"- {item}")
    with st.expander("Common Mistakes"):
        for item in explanation.common_mistakes:
            st.markdown(f"- {item}")
    st.subheader("Summary")
    st.write(explanation.summary)


def render_home() -> None:
    """Render the welcome page and in-memory recent sessions."""

    st.markdown(
        '<div class="hero"><p class="eyebrow">PERSONALIZED LEARNING</p>'
        "<h1>Learn with clarity.<br>Grow with confidence.</h1>"
        "<p>Understand any topic, test your knowledge, and get a learning path "
        "built around your strengths.</p></div>",
        unsafe_allow_html=True,
    )
    if st.button("Start Learning", type="primary"):
        st.session_state.page = "Learning Setup"
        st.rerun()

    st.subheader("Choose your learning style")
    card_one, card_two = st.columns(2)
    with card_one:
        st.markdown(
            '<div class="feature-card"><h3>Learn + Test</h3>'
            "<p>Study a structured explanation first, then test what you learned.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    with card_two:
        st.markdown(
            '<div class="feature-card"><h3>Test First</h3>'
            "<p>Start with a quiz and receive an explanation focused on weak areas.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.subheader("Why learners use it")
    benefit_one, benefit_two, benefit_three = st.columns(3)
    benefit_one.metric("Learn", "Any topic")
    benefit_two.metric("Adapt", "Your level")
    benefit_three.metric("Improve", "With feedback")

    if st.session_state.history:
        st.subheader("Recent Learning Sessions")
        for session in st.session_state.history[-5:]:
            st.write(
                f"**{session['topic']}** — {session['score']:.1f}% "
                f"({session['time']})"
            )


def render_setup() -> None:
    """Collect setup choices and call the selected backend workflow."""

    st.title("Learning Setup")
    st.caption("Step 1 of 4  ·  Tell us what you want to learn.")
    topic = st.text_input(
        "What do you want to learn?",
        value=st.session_state.topic,
        placeholder="Try: Python decorators, personal finance, or climate science",
    )
    level = st.selectbox(
        "Learning level",
        ["Beginner", "Intermediate", "Industry Level"],
        index=["Beginner", "Intermediate", "Industry Level"].index(
            st.session_state.learning_level
        ),
    )
    path = st.radio(
        "Learning path",
        ["Learn + Test", "Test First"],
        horizontal=True,
        index=["Learn + Test", "Test First"].index(st.session_state.learning_path),
    )
    question_count = st.slider("Number of quiz questions", 1, 20, 6)

    if st.button("Generate Learning Material", type="primary"):
        if not topic.strip():
            st.error("Please enter a topic.")
            return

        st.session_state.topic = topic.strip()
        st.session_state.learning_level = level
        st.session_state.learning_path = path
        st.session_state.question_count = question_count
        st.session_state.quiz_evaluation = None
        st.session_state.recommendations = None
        st.session_state.custom_explanation = None
        st.session_state.current_question = 0
        st.session_state.answers = {}

        with st.spinner("Generating learning material..."):
            try:
                if path == "Learn + Test":
                    material = generate_learning_material(
                        topic.strip(), level, question_count
                    )
                    st.session_state.explanation = material["explanation"]
                    st.session_state.quiz = material["quiz"]
                    st.session_state.quiz_started = False
                    st.session_state.page = "Learning Material"
                else:
                    st.session_state.quiz = generate_quiz(
                        topic.strip(), level, question_count
                    )
                    st.session_state.explanation = None
                    st.session_state.quiz_started = True
                    st.session_state.page = "Quiz"

                # --- Persist session start ---
                db_user_id = st.session_state.get("db_user_id", -1)
                if db_user_id and db_user_id > 0:
                    try:
                        mode = "learn_first" if path == "Learn + Test" else "test_first"
                        st.session_state.db_session_id = start_session(
                            db_user_id, topic.strip(), mode, level
                        )
                    except Exception:
                        pass  # DB error — degrade gracefully, do not block UI

                st.rerun()
            except Exception as error:
                show_error("Could not generate learning material. Please try again.")


def render_learning_material() -> None:
    """Show the explanation before allowing access to the quiz."""

    explanation = st.session_state.explanation
    if not isinstance(explanation, TopicExplanation):
        st.info("Generate Learn + Test material first.")
        return

    st.title(st.session_state.topic)
    st.caption("Step 2 of 4  ·  Learn the foundations before your quiz.")
    st.caption(f"Level: {st.session_state.learning_level}")
    display_explanation(explanation)
    if st.button("Start Quiz", type="primary"):
        st.session_state.quiz_started = True
        st.session_state.page = "Quiz"
        st.rerun()


def render_quiz() -> None:
    """Show one public question at a time and preserve answers in session state."""

    quiz = st.session_state.quiz
    if not isinstance(quiz, Quiz):
        st.info("Generate a quiz first.")
        return

    questions = [public_question(question) for question in quiz.questions]
    index = st.session_state.current_question
    question = questions[index]
    question_id = question["question_id"]
    answer_key = f"answer_{question_id}"
    saved_answer = st.session_state.answers.get(question_id, "")
    # Streamlit may remove a widget's temporary state when another question
    # is displayed, so restore the saved answer before creating the widget.
    st.session_state[answer_key] = saved_answer

    def save_answer() -> None:
        """Copy the visible widget value into stable quiz state."""

        st.session_state.answers[question_id] = str(
            st.session_state.get(answer_key, "") or ""
        )

    st.title("Knowledge Check")
    st.caption("Step 3 of 4  ·  Your answers are saved as you move between questions.")
    st.progress((index + 1) / len(questions))
    st.write(f"Question {index + 1} of {len(questions)}")
    st.subheader(question["question_text"])

    if question["question_type"] is QuestionType.MCQ:
        option_index = (
            question["options"].index(saved_answer)
            if saved_answer in question["options"]
            else None
        )
        st.radio(
            "Choose one answer",
            question["options"],
            key=answer_key,
            index=option_index,
            on_change=save_answer,
        )
    elif question["question_type"] is QuestionType.TRUE_FALSE:
        true_false_options = ["True", "False"]
        option_index = (
            true_false_options.index(saved_answer)
            if saved_answer in true_false_options
            else None
        )
        st.radio(
            "Choose True or False",
            true_false_options,
            key=answer_key,
            index=option_index,
            on_change=save_answer,
        )
    else:
        st.text_area(
            "Your answer",
            key=answer_key,
            on_change=save_answer,
        )

    previous, next_column, submit = st.columns(3)
    with previous:
        if st.button("Previous", disabled=index == 0):
            save_answer()
            st.session_state.current_question -= 1
            st.rerun()
    with next_column:
        if st.button("Next", disabled=index == len(questions) - 1):
            save_answer()
            st.session_state.current_question += 1
            st.rerun()
    with submit:
        if st.button("Submit Quiz", type="primary"):
            st.session_state.confirm_submit = True
            st.rerun()

    if st.session_state.confirm_submit:
        st.warning("Submit your quiz now? You will not be able to change answers afterward.")
        confirm, cancel = st.columns(2)
        with confirm:
            if st.button("Confirm Submission", type="primary"):
                st.session_state.confirm_submit = False
                save_answer()
                answers = {
                    item["question_id"]: st.session_state.answers.get(
                        item["question_id"], ""
                    )
                    for item in questions
                }
                with st.spinner("Evaluating your answers..."):
                    try:
                        evaluation = evaluate_quiz(quiz, answers)
                        st.session_state.quiz_evaluation = evaluation

                        # Test First creates its explanation only after evaluation.
                        if st.session_state.learning_path == "Test First":
                            focus = ", ".join(evaluation.weak_concepts)
                            if not focus:
                                focus = "the complete topic"
                            st.session_state.explanation = generate_explanation(
                                f"{st.session_state.topic} (focus on {focus})",
                                st.session_state.learning_level,
                            )

                        # --- Persist quiz results ---
                        db_user_id = st.session_state.get("db_user_id", -1)
                        db_session_id = st.session_state.get("db_session_id")
                        if db_user_id and db_user_id > 0 and db_session_id:
                            try:
                                # Determine attempt type
                                attempt_type = (
                                    "follow_up"
                                    if st.session_state.learning_path == "Test First"
                                    else "initial"
                                )
                                # Build serialisable question results
                                question_results = [
                                    {
                                        "concept_tested": r.concept_tested,
                                        "question_text": next(
                                            (q.question_text for q in quiz.questions if q.question_id == r.question_id),
                                            "",
                                        ),
                                        "question_type": next(
                                            (q.question_type.value for q in quiz.questions if q.question_id == r.question_id),
                                            "MCQ",
                                        ),
                                        "user_answer": r.user_answer,
                                        "correct_answer": r.correct_answer,
                                        "is_correct": r.is_correct,
                                        "explanation": r.explanation,
                                    }
                                    for r in evaluation.question_results
                                ]
                                save_quiz_attempt(
                                    db_session_id,
                                    attempt_type,
                                    question_results,
                                    evaluation.score_percentage,
                                )
                                update_concept_progress(
                                    db_user_id,
                                    st.session_state.topic,
                                    question_results,
                                )
                                # Generate and cache adaptive recommendations
                                profile = get_learner_profile(db_user_id)
                                st.session_state.learner_profile = profile
                                rec_set = generate_recommendations(
                                    profile,
                                    st.session_state.topic,
                                    evaluation.score_percentage,
                                )
                                st.session_state.adaptive_recommendations = rec_set
                            except Exception:
                                pass  # DB error — degrade gracefully

                        st.session_state.history.append(
                            {
                                "topic": st.session_state.topic,
                                "score": evaluation.score_percentage,
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            }
                        )
                        st.session_state.page = "Results"
                        st.rerun()
                    except Exception:
                        show_error("Could not evaluate the quiz. Please try again.")
        with cancel:
            if st.button("Keep Editing"):
                st.session_state.confirm_submit = False
                st.rerun()


def render_results() -> None:
    """Display the validated evaluation report after submission."""

    evaluation = st.session_state.quiz_evaluation
    if not isinstance(evaluation, QuizEvaluation):
        st.info("Submit a quiz to see results.")
        return

    st.markdown(
        '<div class="results-header"><h2>Your Learning Results</h2>'
        "<p>Review your performance, understand your mistakes, and choose your next step.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Step 4 of 4  ·  Topic: " + st.session_state.topic)
    first, second, third = st.columns(3)
    first.metric("Score", f"{evaluation.score_percentage:.1f}%")
    second.metric("Correct", evaluation.correct_answers)
    third.metric("Incorrect", evaluation.incorrect_answers)
    st.write("")
    st.progress(evaluation.score_percentage / 100)

    feedback_tab, improvement_tab, explanation_tab = st.tabs(
        ["Question Feedback", "Improvement Plan", "Topic Explanation"]
    )
    with feedback_tab:
        st.markdown('<h3 class="section-heading">Question Feedback</h3>', unsafe_allow_html=True)
        for result in evaluation.question_results:
            status = "Correct" if result.is_correct else "Needs review"
            style = "feedback-correct" if result.is_correct else "feedback-incorrect"
            with st.expander(f"Question {result.question_id}  ·  {status}"):
                st.markdown(f'<div class="content-card {style}">', unsafe_allow_html=True)
                st.write(f"**Your answer:** {result.user_answer or 'No answer'}")
                st.write(f"**Correct answer:** {result.correct_answer}")
                st.write(result.explanation)
                st.markdown("</div>", unsafe_allow_html=True)

    with improvement_tab:
        st.markdown('<h3 class="section-heading">Focus Areas</h3>', unsafe_allow_html=True)
        if evaluation.weak_concepts:
            for concept in evaluation.weak_concepts:
                st.info(concept)
        else:
            st.success("Great work! No weak concepts were identified.")
        st.markdown('<h3 class="section-heading">Improvement Suggestions</h3>', unsafe_allow_html=True)
        for suggestion in evaluation.improvement_suggestions:
            st.markdown(f"- {suggestion}")

    with explanation_tab:
        st.markdown('<h3 class="section-heading">Explanation for Your Learning Path</h3>', unsafe_allow_html=True)
        if isinstance(st.session_state.explanation, TopicExplanation):
            display_explanation(st.session_state.explanation)
        else:
            st.info("Your personalized explanation is not available.")

    st.markdown('<h3 class="section-heading">Continue Learning</h3>', unsafe_allow_html=True)
    explore, new_quiz = st.columns(2)
    with explore:
        if st.button("Explore More Topics", type="primary"):
            # Mark session complete when user moves forward
            db_session_id = st.session_state.get("db_session_id")
            if db_session_id:
                try:
                    complete_session(db_session_id)
                except Exception:
                    pass
            st.session_state.page = "Further Learning"
            st.rerun()
    with new_quiz:
        if st.button("Start Another Quiz"):
            reset_learning_session()
            st.rerun()

    # --- Adaptive Recommendations ---
    rec_set = st.session_state.get("adaptive_recommendations")
    if rec_set and not rec_set.is_empty:
        st.markdown('<h3 class="section-heading">📊 Personalised Recommendations</h3>', unsafe_allow_html=True)
        if rec_set.revision:
            st.markdown("**📖 Concepts to Revise**")
            for rec in rec_set.revision:
                st.info(f"**{rec.title}**\n\n{rec.reasoning}")
        if rec_set.practice:
            st.markdown("**🎯 Targeted Practice**")
            for rec in rec_set.practice:
                st.warning(f"**{rec.title}**\n\n{rec.reasoning}")
        if rec_set.next_topic:
            st.markdown("**🚀 Ready for More?**")
            for rec in rec_set.next_topic:
                st.success(f"**{rec.title}**\n\n{rec.reasoning}")


def render_further_learning() -> None:
    """Generate recommendations and support recommended or custom topics."""

    evaluation = st.session_state.quiz_evaluation
    if not isinstance(evaluation, QuizEvaluation):
        st.info("Complete a quiz before exploring further learning.")
        return

    st.title("Your Next Learning Steps")
    st.caption("Build on your results with related topics and practical activities.")

    # --- Adaptive Practice Quiz ---
    db_user_id = st.session_state.get("db_user_id", -1)
    topic = st.session_state.topic
    if db_user_id and db_user_id > 0 and topic:
        weak = get_weak_concepts_for_topic(db_user_id, topic)
        if weak:
            st.markdown("---")
            st.subheader("🎯 Adaptive Practice Quiz")
            st.write(
                f"You have **{len(weak)} weak concept(s)** in **{topic}**: "
                + ", ".join(f"`{c}`" for c in weak[:5])
            )
            if st.button("Start Adaptive Practice Quiz", type="primary"):
                with st.spinner("Building your personalised quiz..."):
                    try:
                        ctx = build_quiz_context(
                            db_user_id,
                            topic,
                            st.session_state.question_count,
                            st.session_state.learning_level,
                        )
                        st.session_state.quiz = generate_adaptive_quiz(
                            topic=ctx["topic"],
                            learning_level=ctx["learning_level"] if ctx["learning_level"] else st.session_state.learning_level,
                            question_count=ctx["question_count"],
                            weak_concepts=ctx["weak_concepts"],
                            mastered_concepts=ctx["mastered_concepts"],
                            incorrect_history=ctx["incorrect_history"],
                            has_history=ctx["has_history"],
                        )
                        # Reset quiz state for the new adaptive quiz
                        st.session_state.quiz_evaluation = None
                        st.session_state.quiz_started = True
                        st.session_state.current_question = 0
                        st.session_state.answers = {}
                        st.session_state.confirm_submit = False
                        st.session_state.adaptive_recommendations = None
                        st.session_state.page = "Quiz"
                        st.rerun()
                    except Exception:
                        show_error("Could not generate the adaptive quiz. Please try again.")
            st.markdown("---")

    if st.button("Explore More", type="primary"):
        with st.spinner("Finding your next topics..."):
            try:
                st.session_state.recommendations = generate_learning_recommendations(
                    st.session_state.topic,
                    st.session_state.learning_level,
                    evaluation,
                )
                st.rerun()
            except Exception as error:
                show_error("Could not generate learning recommendations. Please try again.")

    recommendations = st.session_state.recommendations
    if recommendations:
        st.subheader("Recommended Topics")
        for item in recommendations.recommended_topics:
            st.markdown(f"- {item}")
        st.subheader("Advanced Topics")
        for item in recommendations.advanced_topics:
            st.markdown(f"- {item}")
        st.subheader("Suggested Learning Order")
        for item in recommendations.suggested_learning_order:
            st.markdown(f"- {item}")

        if recommendations.recommended_topics:
            selected = st.selectbox(
                "Choose a recommended topic",
                recommendations.recommended_topics,
            )
            if st.button("Learn Recommended Topic"):
                with st.spinner("Generating the explanation..."):
                    try:
                        st.session_state.custom_explanation = generate_explanation(
                            selected, st.session_state.learning_level
                        )
                        st.rerun()
                    except Exception as error:
                        show_error("Could not generate the recommended explanation.")

    custom_topic = st.text_input("Or enter your own topic")
    if st.button("Continue Custom Learning"):
        if not custom_topic.strip():
            st.error("Please enter a custom topic.")
        else:
            with st.spinner("Generating the explanation..."):
                try:
                    st.session_state.custom_explanation = generate_custom_learning(
                        custom_topic, st.session_state.learning_level
                    )
                    st.rerun()
                except Exception as error:
                    show_error("Could not generate the custom explanation.")

    if isinstance(st.session_state.custom_explanation, TopicExplanation):
        st.subheader(st.session_state.custom_explanation.topic)
        display_explanation(st.session_state.custom_explanation)


def render_settings() -> None:
    """Show safe, non-secret application settings."""

    st.title("Settings")
    st.write("The Groq API key is loaded from the environment and is never displayed.")
    st.write("Model configuration is controlled by the GROQ_MODEL environment variable.")


def render_history() -> None:
    """Display sessions kept in this browser session only."""

    st.title("My Learning History")
    if not st.session_state.history:
        st.info("No completed learning sessions yet.")
        return
    for session in reversed(st.session_state.history):
        st.write(
            f"**{session['topic']}** — {session['score']:.1f}% "
            f"({session['time']})"
        )


initialize_state()

pages = [
    "Home",
    "Learning Setup",
    "Learning Material",
    "Quiz",
    "Results",
    "Further Learning",
    "My Learning History",
    "Settings",
]
current_page = st.sidebar.radio(
    "Navigate",
    pages,
    index=pages.index(st.session_state.page),
)
st.session_state.page = current_page

if st.sidebar.button("New Learning Session"):
    reset_learning_session()
    st.rerun()

if current_page == "Home":
    render_home()
elif current_page == "Learning Setup":
    render_setup()
elif current_page == "Learning Material":
    render_learning_material()
elif current_page == "Quiz":
    render_quiz()
elif current_page == "Results":
    render_results()
elif current_page == "Further Learning":
    render_further_learning()
elif current_page == "My Learning History":
    render_history()
else:
    render_settings()
