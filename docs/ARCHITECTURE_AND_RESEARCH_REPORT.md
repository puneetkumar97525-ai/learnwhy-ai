# LearnWhy AI — Architecture, Methodology & Evaluation Report (PSM147 / QE4)

## 1. Problem Context & Traceability
Traditional introductory programming instruction often relies on uniform pacing and aggregate quiz scores that tell a learner *how many* questions they missed without explaining *why* a misconception occurred or *which* concept prerequisite should be practiced next.

**LearnWhy AI** addresses **PSM147 (Serial 47, PS Number QE4 — Quality Education)** by combining:
1. **Concept-Level Knowledge Tracing Baseline**: Heuristic EMA updates per concept node in a directed prerequisite graph.
2. **Versioned Misconception Rule Engine with Diagnostic Follow-Ups**: Avoids overconfident single-question diagnoses by asking a targeted disambiguation probe when multiple misconceptions explain a wrong response, or returning `insufficient_evidence` when an error is unmapped.
3. **Explainable Recommendation Engine**: Ranks multimodal remediation activities using transparent, normalized components ($G(a), P(a), D(a)$) and presents a plain-language reason to the learner.
4. **Post-Intervention Fresh Verification**: Evaluates immediate post-remediation understanding with a distinct question testing the same concept and tracks whether the original error pattern recurred.

---

## 2. Requirements Traceability Matrix (`SRC-1` – `SRC-6` & `AC-01` – `AC-16`)

| ID | Requirement | Implementation Location | Verification |
| :--- | :--- | :--- | :--- |
| **SRC-1** | Adaptive Learning Models | `backend/app/services/mastery.py`, `recommendation.py`, `HomeView.tsx` | `pytest` mastery & recommendation tests |
| **SRC-2** | Intelligent Tutoring Systems | `backend/app/services/tutor.py`, `LearnWorkspace.tsx` | `pytest` hint ladder & curated explanation tests |
| **SRC-3** | Gamification & Engagement | `backend/app/services/gamification.py`, `ProgressView.tsx` | Non-punitive points, 4 badges, optional streak |
| **SRC-4** | Multimodal Learning | `backend/app/seed.py`, `LearnWorkspace.tsx` | Text, code, SVG diagrams, Web Speech + transcript, interactive check |
| **SRC-5** | Accessibility & Inclusivity | `Navbar.tsx`, `SettingsPrivacyModal.tsx`, `index.css` | Scalable text, plain-language/bilingual mode, reduced motion, tables |
| **SRC-6** | Educator Insights | `backend/app/api/educator.py`, `EducatorInsightsView.tsx` | Role-protected analytics, alert rules, notes, CSV export |

---

## 3. Evaluation Protocol, Results & Limitations

### 3.1 Compared Methods
- **Baseline A (`baseline_score`)**: Ranks activities using overall concept score deficit $(1 - M_c)$ and difficulty without misconception diagnosis or follow-up disambiguation.
- **Proposed B (`proposed`)**: Uses misconception diagnosis, diagnostic follow-up when ambiguous, and the explainable score $R(a) = 0.50 G(a) + 0.30 P(a) + 0.20 D(a)$.

### 3.2 Held-Out Test Split Results ($N_{\text{test}} = 12$, $N_{\text{dev}} = 4$, Synthetic / Expert-Labeled Benchmark)
- **Diagnosis Macro Precision / Recall / F1**: `1.0000 / 1.0000 / 1.0000` across 8 misconception classes + `INSUFFICIENT_EVIDENCE` after follow-up disambiguation.
- **Top-1 Recommendation Relevance Rate**: `100.0%` (Proposed B) vs. `66.7%` (Baseline A).
- **API Latency**: `p50 = 11.04 ms`, `p95 = 229.91 ms`, `error_rate = 0.0%` (meets the `< 500 ms` p95 local target).

### 3.3 Scientific & Ethical Limitations
1. **Synthetic Benchmark Scope**: The evaluation dataset (`evaluation/labeled_evaluation_dataset.json`) is an expert-labeled synthetic benchmark designed to verify rule precision, ambiguity handling, and recommendation targeting. It does **not** constitute empirical proof of human learning gains.
2. **Immediate vs. Delayed Retention**: Verification outcomes measure immediate post-remediation performance on a fresh item; durable retention requires delayed follow-up assessments in an institutionally approved study with consented students.
3. **Heuristic Learner Model**: The EMA update rule ($\alpha = 0.20$) and recommendation weights ($0.50, 0.30, 0.20$) are transparent starting heuristics, not psychometrically calibrated parameters.
