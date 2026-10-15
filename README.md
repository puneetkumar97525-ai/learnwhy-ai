# LearnWhy AI

**An Explainable, Misconception-Aware Personalized Learning Platform Using Knowledge Tracing and Adaptive Remediation**

MCA project: **PSM147 (Serial 47) · PS Number QE4 · Quality Education**

> Repository status: project documentation is being set up first. Add the full frontend/backend source tree before treating this as a runnable application. Reported test/evaluation results should be reproducible from committed code before being claimed as independently verified.

## Overview

LearnWhy AI is designed to personalize Python learning with an explainable loop:

1. Learner answers a concept-focused question.
2. The system diagnoses a likely misconception.
3. If competing explanations are plausible, it asks a diagnostic follow-up.
4. It recommends a targeted activity and explains why.
5. A fresh question verifies the same concept.
6. Mastery estimates and progress are updated.

The project also includes an educator dashboard for aggregate learning insights and supportive review.

## Six required considerations

- **Adaptive learning models:** concept-level mastery, prerequisite relationships, adaptive difficulty.
- **Intelligent tutoring systems:** progressive hints, worked examples, and misconception-specific explanations.
- **Gamification and engagement:** practice goals, optional streaks, points, and milestone badges; learning content is not locked behind rewards.
- **Multimodal learning:** readable text, annotated code, diagrams, optional audio narration, and interactive checks. These are presentation choices, not fixed learner “types.”
- **Accessibility and inclusivity:** keyboard support, visible focus, scalable typography, reduced motion, high contrast, plain language, and English/Hindi support.
- **Data-driven educator insights:** cohort summaries, concept mastery, recurring misconceptions, supportive-review flags, and aggregate CSV export.

## Architecture

- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI
- Persistence: SQLAlchemy 2.x and Alembic
- Database: SQLite for local development; PostgreSQL supported through configuration
- Tests: pytest and Vitest
- Tutor: deterministic curated content by default; optional server-side LLM adapter

## Methods

### Mastery update

The implementation report describes this configurable moving-average heuristic:

`M_new = (1 - alpha) * M_old + alpha * y`

Here `y` is 1 for a correct response and 0 otherwise; the reported default is `alpha = 0.20`. This is a project heuristic, not a validated cognitive model.

### Explainable recommendation

`R(a) = 0.50 * G + 0.30 * P + 0.20 * D`

- `G`: gap relevance
- `P`: prerequisite importance
- `D`: difficulty fit

The weights are initial design choices that should be evaluated and tuned. A score-based baseline is included in the reported design for comparison. Synthetic evaluation must be labeled synthetic and is not evidence of real-world learning gains.

## Local development

These commands require the corresponding source files to be committed first.

### Environment

Copy `.env.example` to `.env` and replace the placeholder secret with a unique random value.

### Initialize the database

```bash
cd backend
alembic upgrade head
python -m app.seed
```

### Start the API

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Start the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

### Run tests and evaluation

```bash
cd backend
pytest -v
```

```bash
cd frontend
npm run test
```

```bash
python evaluation/evaluate_methods.py
```

## Security and privacy

- Never commit `.env`, credentials, API keys, local database files, or real student data.
- Keep LLM keys server-side; never expose them in browser code.
- Do not execute arbitrary learner-submitted Python on the application server.
- Use synthetic or properly de-identified data for demos.
- Obtain consent and appropriate institutional approval for human-subject studies.
- Check repository visibility before uploading code or datasets.

## Deferred work and limitations

The implementation report says live external LLM generation is not configured by default, arbitrary student code execution is intentionally excluded, and delayed-retention claims require a future approved study with consented participants.

## Academic reporting

Document the evaluation setup, dataset size, limitations, and reproducible results transparently. Synthetic benchmark performance must not be presented as proof of long-term learning effectiveness.
