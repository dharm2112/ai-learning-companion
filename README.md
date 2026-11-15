# AI Learning Companion

An incremental Streamlit learning application powered by LangChain and Groq.

## Phase 1 setup

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Configure the key safely:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edit `.env` and set `GROQ_API_KEY`. The `.gitignore` prevents `.env` from
   being committed.

4. Start the app:

   ```powershell
   streamlit run app.py
   ```

## Planned architecture

- `config.py`: validated environment-backed settings.
- `services/`: provider and business services; Phase 1 contains Groq model creation.
- `schemas/`: Pydantic models for validated generated content.
- `prompts/`: reusable prompt templates.
- `chains/`: composable LangChain LCEL pipelines.
- `utils/`: session and validation helpers.
- `app.py`: Streamlit presentation layer.

## Phase 2: schemas and structured output

Pydantic `BaseModel` classes define the validated shape of explanations, quizzes,
evaluations, and further-learning recommendations. `Field` adds constraints and
descriptions, while `model_validator` enforces rules involving multiple fields,
such as unique question IDs and consistent quiz scores. Nested models allow a
`Quiz` to contain validated `QuizQuestion` objects.

Ordinary model output is unstructured text that the application must parse itself.
LangChain's `with_structured_output()` asks the chat model for a schema-conforming
response and parses it into a Pydantic object. The Phase 2 experiment is available
at `experiments/structured_output.py`.

Quiz answer keys remain in the backend `QuizQuestion` model. A later UI phase must
map questions to a separate public schema without `correct_answer`, preventing
answers from being sent to the browser before submission.

Example input:

```text
Explain Python functions for a beginner and populate every required field.
```

Example structured result:

```python
TopicExplanation(
    topic="Python Functions",
    learning_level="Beginner",
    definition="A reusable named block of Python code.",
    key_concepts=["def", "parameters", "return values"],
    # Other required fields are also validated.
)
```

## Phase 3: explanation generation chain

The explanation prompt is kept in `prompts/explanation_prompt.py` so the wording
can be changed without mixing it with Python chain logic. The prompt receives
`topic` and `learning_level` variables at runtime. The learning-level instructions
tell the model how much detail and which engineering concerns to include.

`chains/explanation_chain.py` connects the prompt to the existing ChatGroq model:

```python
chain = EXPLANATION_PROMPT | llm.with_structured_output(TopicExplanation)
result = chain.invoke({"topic": "Python", "learning_level": "Beginner"})
```

The pipe creates an LCEL `RunnableSequence`. `invoke()` sends the formatted
messages to ChatGroq, receives structured output, and validates it as a
`TopicExplanation` Pydantic object. The same function can later be reused by
Learn + Test and Test First follow-up workflows.

Run the manual experiment with:

```powershell
.\.venv\Scripts\python.exe experiments\test_explanation.py
```

## Phase 4: quiz generation chain

The quiz chain uses the same simple pattern:

```python
chain = QUIZ_PROMPT | llm.with_structured_output(Quiz, method="json_schema")
quiz = chain.invoke({
    "topic": "Python",
    "learning_level": "Beginner",
    "question_count": 6,
    "distribution": "3 MCQ, 2 True/False, 1 Short Answer",
})
```

`generate_quiz()` validates the user inputs first. It then formats the prompt,
calls Groq, validates the response as a `Quiz`, and checks that the returned
question count exactly matches the request. The complete quiz, including
`correct_answer`, remains a backend object and is not sent to a frontend in this
phase.

Run the developer experiment with:

```powershell
.\.venv\Scripts\python.exe -m experiments.test_quiz
```

## Phase 5: parallel learning material

`chains/parallel_chain.py` uses `RunnableParallel` to run the existing
explanation and quiz chains concurrently:

```python
RunnableParallel(
    explanation=explanation_input | get_explanation_chain(),
    quiz=quiz_input | get_quiz_chain(),
)
```

Each branch receives the same original input dictionary, but a small
`RunnableLambda` selects the keys required by that branch. The parallel result
is one dictionary with `explanation` and `quiz` values. The function then checks
that both values are the expected Pydantic types.

Sequential code waits for the explanation before starting the quiz:

```python
explanation = explanation_chain.invoke(data)
quiz = quiz_chain.invoke(data)
```

`RunnableParallel` starts independent branches together, so total waiting time
can be closer to the slower branch instead of the sum of both model calls.
This differs from `RunnableSequence`, where each step waits for the previous
step and passes its output to the next step.

Run the manual experiment with:

```powershell
.\.venv\Scripts\python.exe -m experiments.test_parallel
```

## Phase 6: quiz evaluation

MCQ and True/False answers are checked with normal Python because their answer
rules are deterministic, fast, and reproducible. Only non-empty Short Answer
responses use Groq. The short-answer prompt asks Groq for a
`ShortAnswerEvaluation` Pydantic object, and the final results are stored as
`QuestionResult` objects inside a validated `QuizEvaluation`.

The evaluation flow is:

```text
Quiz + user_answers
        ↓
MCQ/True-False: Python comparison
Short Answer: EVALUATION_PROMPT | structured ChatGroq
        ↓
QuestionResult objects
        ↓
QuizEvaluation with score and weak concepts
```

Unknown question IDs are rejected, while missing answers are treated as
incorrect. Correct answers always come from the original backend `Quiz`; they
are never accepted from the submitted answer dictionary.

Run the developer experiment with:

```powershell
.\.venv\Scripts\python.exe -m experiments.test_evaluation
```

## Phase 7: further learning

`generate_learning_recommendations()` sends the current topic, learning level,
score, weak concepts, and improvement suggestions through a
`ChatPromptTemplate`. The structured result is a validated `FurtherLearning`
object.

The custom-learning workflow does not create another explanation implementation.
It calls the existing explanation chain with the learner's selected topic:

```python
generate_custom_learning(
    "RunnableBranch with practical examples",
    "Intermediate",
)
```

Run the developer experiment with:

```powershell
.\.venv\Scripts\python.exe -m experiments.test_learning
```

## Phase 8: Streamlit UI

The Streamlit app in `app.py` is a thin presentation layer over the existing
chains. It stores the current page, generated backend objects, quiz progress,
answers, evaluation, recommendations, and in-memory history in
`st.session_state`. Model calls happen only inside button handlers, so normal
reruns do not generate new content.

Before quiz submission, the UI converts each backend question into a small
public dictionary containing only `question_id`, `question_text`,
`question_type`, and `options`. The original `Quiz` object stays in session
state and is passed directly to `evaluate_quiz()` after submission. This keeps
answer keys out of the question widgets.

Start the application with:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```
