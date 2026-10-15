import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import rate_limiter
from app.main import app
from app.models.entities import Attempt, Concept, Course, MasteryState, Question, User
from app.seed import seed_database
from app.services.mastery import compute_ema_mastery


@pytest.fixture()
def client():
    rate_limiter.reset()
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(test_engine, "connect")
    def _fk_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine, future=True
    )
    app.state.test_session_local = TestingSessionLocal
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as session:
        seed_database(session)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_and_published_content_integrity(client: TestClient):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["llm_tutor_adapter"] == "deterministic_curated_fallback"

    admin_headers = _login(client, "vikram.admin@demo.learnwhy.edu", "AdminPass123!")
    overview = client.get("/api/admin/overview", headers=admin_headers).json()
    assert len(overview["concepts"]) >= 6
    for q in overview["questions"]:
        if q["status"] == "published":
            assert q["answer_key"]
            assert q["explanation"]
            assert q["concept_id"] > 0
            assert any(o["is_correct"] for o in q["options"])


def test_mastery_update_formula_and_concept_isolation(client: TestClient):
    # Pure unit check of M_new = (1 - alpha) * M_old + alpha * y
    assert compute_ema_mastery(0.40, True, alpha=0.20) == pytest.approx(0.52)
    assert compute_ema_mastery(0.40, False, alpha=0.20) == pytest.approx(0.32)

    # Register a fresh student to verify concept isolation on attempt
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "fresh.learner@demo.learnwhy.edu",
            "password": "Password123!",
            "full_name": "Fresh Learner",
            # Attempt privilege escalation; public registration must ignore this.
            "role": "admin",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["user"]["role"] == "student"
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    assert client.get("/api/admin/overview", headers=headers).status_code == 403

    courses = client.get("/api/courses").json()["courses"]
    course_id = courses[0]["id"]
    before_concepts = {
        c["slug"]: c
        for c in client.get(
            f"/api/courses/{course_id}/concepts", headers=headers
        ).json()["concepts"]
    }

    # Fetch question for 'variables-expressions'
    var_cid = before_concepts["variables-expressions"]["id"]
    q_res = client.get(f"/api/questions/next?concept_id={var_cid}", headers=headers)
    assert q_res.status_code == 200
    q_id = q_res.json()["question"]["id"]

    # Submit correct answer ('B' for PY-VAR-01)
    att_res = client.post(
        "/api/attempts",
        headers=headers,
        json={"question_id": q_id, "response": "B", "hints_used": 0},
    )
    assert att_res.status_code == 200
    att_data = att_res.json()
    assert att_data["is_correct"] is True
    assert att_data["mastery_update"]["new_mastery"] > att_data["mastery_update"]["previous_mastery"]

    # Verify ONLY 'variables-expressions' mastery changed; 'conditions' and 'loops' are untouched
    after_concepts = {
        c["slug"]: c
        for c in client.get(
            f"/api/courses/{course_id}/concepts", headers=headers
        ).json()["concepts"]
    }
    assert (
        after_concepts["variables-expressions"]["mastery"]
        > before_concepts["variables-expressions"]["mastery"]
    )
    assert (
        after_concepts["conditions"]["mastery"]
        == before_concepts["conditions"]["mastery"]
    )
    assert (
        after_concepts["loops"]["mastery"] == before_concepts["loops"]["mastery"]
    )


def test_diagnosis_confident_ambiguous_followup_and_insufficient_evidence(
    client: TestClient,
):
    headers = _login(client, "aarav.student@demo.learnwhy.edu", "StudentPass123!")
    admin_headers = _login(client, "vikram.admin@demo.learnwhy.edu", "AdminPass123!")
    questions_by_sid = {
        q["stable_id"]: q
        for q in client.get("/api/admin/overview", headers=admin_headers).json()["questions"]
    }

    # 1. Confident single-misconception diagnosis on PY-COND-01 with option 'A'
    q_cond = questions_by_sid["PY-COND-01"]
    res_conf = client.post(
        "/api/attempts",
        headers=headers,
        json={"question_id": q_cond["id"], "response": "A"},
    )
    assert res_conf.status_code == 200
    diag_conf = res_conf.json()["diagnosis"]
    assert diag_conf["status"] == "diagnosed"
    assert diag_conf["misconception"]["code"] == "MISC-COND-ELIF-CHAIN"
    assert diag_conf["confidence"] >= 0.75
    assert diag_conf["rule_version"] == "v1.0.0-rules"

    # 2. Ambiguous response on PY-LOOP-01 with option 'A' -> triggers diagnostic follow-up!
    q_loop = questions_by_sid["PY-LOOP-01"]
    res_amb = client.post(
        "/api/attempts",
        headers=headers,
        json={"question_id": q_loop["id"], "response": "A"},
    )
    assert res_amb.status_code == 200
    amb_body = res_amb.json()
    diag_amb = amb_body["diagnosis"]
    assert diag_amb["status"] == "ambiguous_followup_needed"
    assert diag_amb["requires_diagnostic_followup"] is True
    assert len(diag_amb["candidate_misconceptions"]) == 2
    followup_q = diag_amb["followup_question"]
    assert followup_q is not None
    assert followup_q["stable_id"] == "PY-LOOP-FOLLOWUP-01"

    # Submit diagnostic follow-up response 'B' ([2, 3, 4, 5]) confirming MISC-LOOP-RANGE-STOP
    res_fu = client.post(
        f"/api/attempts/{amb_body['attempt_id']}/diagnostic-follow-up",
        headers=headers,
        json={"followup_question_id": followup_q["id"], "response": "B"},
    )
    assert res_fu.status_code == 200
    fu_diag = res_fu.json()["diagnosis"]
    assert fu_diag["status"] == "resolved_by_followup"
    assert fu_diag["misconception"]["code"] == "MISC-LOOP-RANGE-STOP"
    assert fu_diag["confidence"] == pytest.approx(0.88)

    # 3. Unmapped wrong answer on PY-VAR-01 with option 'C' -> returns 'insufficient_evidence'
    q_var = questions_by_sid["PY-VAR-01"]
    res_insuff = client.post(
        "/api/attempts",
        headers=headers,
        json={"question_id": q_var["id"], "response": "C"},
    )
    assert res_insuff.status_code == 200
    diag_insuff = res_insuff.json()["diagnosis"]
    assert diag_insuff["status"] == "insufficient_evidence"
    assert diag_insuff["misconception"] is None


def test_recommendation_ranking_and_verification_loop(client: TestClient):
    headers = _login(client, "aarav.student@demo.learnwhy.edu", "StudentPass123!")

    # Compare proposed vs baseline_score recommendations
    rec_prop = client.get("/api/recommendations?strategy=proposed", headers=headers)
    assert rec_prop.status_code == 200
    prop_list = rec_prop.json()["recommendations"]
    assert len(prop_list) >= 1
    top_rec = prop_list[0]
    comps = top_rec["score_components"]
    assert 0.0 <= comps["gap_relevance"] <= 1.0
    assert 0.0 <= comps["prerequisite_importance"] <= 1.0
    assert 0.0 <= comps["difficulty_fit"] <= 1.0
    expected_score = (
        0.50 * comps["gap_relevance"]
        + 0.30 * comps["prerequisite_importance"]
        + 0.20 * comps["difficulty_fit"]
    )
    assert top_rec["total_score"] == pytest.approx(expected_score, abs=1e-3)
    assert "Recommended because" in top_rec["reason"]

    rec_base = client.get(
        "/api/recommendations?strategy=baseline_score", headers=headers
    )
    assert rec_base.status_code == 200
    assert len(rec_base.json()["recommendations"]) >= 1

    # Complete the top recommended intervention
    rec_id = top_rec["id"]
    comp_res = client.post(
        f"/api/interventions/{rec_id}/complete",
        headers=headers,
        json={"completion_seconds": 120, "format_used": "multimodal"},
    )
    assert comp_res.status_code == 200
    verif_q = comp_res.json()["verification_question"]
    assert verif_q["id"] > 0

    # Find the correct option from admin view to verify positive mastery update
    admin_headers = _login(client, "vikram.admin@demo.learnwhy.edu", "AdminPass123!")
    q_admin = next(
        q
        for q in client.get("/api/admin/overview", headers=admin_headers).json()["questions"]
        if q["id"] == verif_q["id"]
    )
    correct_key = q_admin["answer_key"]

    ver_res = client.post(
        f"/api/interventions/{rec_id}/verify",
        headers=headers,
        json={
            "verification_question_id": verif_q["id"],
            "response": correct_key,
            "completion_seconds": 65,
        },
    )
    assert ver_res.status_code == 200
    ver_body = ver_res.json()
    assert ver_body["is_correct"] is True
    assert ver_body["immediate_outcome"] == "improved"
    assert ver_body["error_recurred"] is False
    assert (
        ver_body["mastery_update"]["post_mastery"]
        > ver_body["mastery_update"]["pre_mastery"]
    )
    assert "long-term retention" in ver_body["retention_disclaimer"]


def test_role_permissions_educator_and_admin(client: TestClient):
    student_headers = _login(
        client, "aarav.student@demo.learnwhy.edu", "StudentPass123!"
    )
    educator_headers = _login(
        client, "meera.educator@demo.learnwhy.edu", "EducatorPass123!"
    )
    admin_headers = _login(
        client, "vikram.admin@demo.learnwhy.edu", "AdminPass123!"
    )

    # Student must be blocked from educator and admin routes
    assert (
        client.get(
            "/api/educator/classes/1/analytics", headers=student_headers
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/educator/classes/1/export", headers=student_headers
        ).status_code
        == 403
    )
    assert (
        client.get("/api/admin/overview", headers=student_headers).status_code
        == 403
    )

    # Add a second course and learner to prove both authorization and cohort scoping.
    baseline = client.get("/api/educator/classes/1/analytics", headers=educator_headers)
    assert baseline.status_code == 200
    baseline_summary = baseline.json()["summary"]
    with app.state.test_session_local() as db:
        other_course = Course(
            slug="unassigned-course-test", title="Unassigned Course",
            description="A separate test cohort.", status="published", version="1.0.0",
        )
        db.add(other_course)
        db.flush()
        other_student = User(
            email="other.cohort.student@example.test", full_name="Other Cohort Student",
            password_hash="unused-test-hash", role="student", status="active",
            selected_course_id=other_course.id,
        )
        db.add(other_student)
        db.flush()
        first_course_question = db.query(Question).first()
        db.add(Attempt(
            user_id=other_student.id, question_id=first_course_question.id,
            response="A", is_correct=False, attempt_context="privacy-scope-test",
        ))
        other_course_id = other_course.id
        db.commit()

    # Educator is not assigned to the second, existing course.
    assert client.get(f"/api/educator/classes/{other_course_id}/analytics", headers=educator_headers).status_code == 403
    assert client.get(f"/api/educator/classes/{other_course_id}/export", headers=educator_headers).status_code == 403
    after = client.get("/api/educator/classes/1/analytics", headers=educator_headers)
    assert after.status_code == 200
    assert after.json()["summary"]["active_students"] == baseline_summary["active_students"] == 3
    assert after.json()["summary"]["total_attempts"] == baseline_summary["total_attempts"]

    # Unknown classes also fail closed.
    assert client.get("/api/educator/classes/999/analytics", headers=educator_headers).status_code == 404

    # Educator can view class analytics & export CSV, but cannot access admin content CRUD
    edu_analytics = client.get(
        "/api/educator/classes/1/analytics", headers=educator_headers
    )
    assert edu_analytics.status_code == 200
    assert "concept_performance" in edu_analytics.json()
    assert "common_misconceptions" in edu_analytics.json()

    edu_csv = client.get(
        "/api/educator/classes/1/export", headers=educator_headers
    )
    assert edu_csv.status_code == 200
    assert "text/csv" in edu_csv.headers["content-type"]
    assert "Concept Performance" in edu_csv.text

    assert (
        client.get("/api/admin/overview", headers=educator_headers).status_code
        == 403
    )

    # Admin can create and archive a question
    create_q = client.post(
        "/api/admin/questions",
        headers=admin_headers,
        json={
            "stable_id": "PY-VAR-ADMIN-TEST",
            "concept_id": 1,
            "difficulty": 1,
            "content": "What is the type of 42 in Python?",
            "code_snippet": "x = 42\nprint(type(x))",
            "answer_key": "A",
            "explanation": "Whole numbers without decimals have type int in Python.",
            "hint_ladder": ["Check whether 42 has a decimal point or quotes."],
            "options": [
                {"option_key": "A", "option_text": "<class 'int'>", "is_correct": True},
                {"option_key": "B", "option_text": "<class 'str'>", "is_correct": False},
            ],
        },
    )
    assert create_q.status_code == 201
    new_qid = create_q.json()["id"]

    arch_q = client.post(
        f"/api/admin/questions/{new_qid}/archive", headers=admin_headers
    )
    assert arch_q.status_code == 200
    assert arch_q.json()["status"] == "archived"


def test_preferences_tutor_hints_educator_acknowledge_and_privacy_export(
    client: TestClient,
):
    student_headers = _login(
        client, "aarav.student@demo.learnwhy.edu", "StudentPass123!"
    )
    educator_headers = _login(
        client, "meera.educator@demo.learnwhy.edu", "EducatorPass123!"
    )

    # Update accessibility & multimodal preferences
    pref_res = client.put(
        "/api/auth/preferences",
        headers=student_headers,
        json={
            "selected_course_id": 1,
            "language": "bilingual",
            "text_size": "large",
            "reduced_motion": True,
            "high_contrast": True,
            "plain_language_mode": True,
            "preferred_formats": ["text", "diagram", "audio"],
            "daily_goal_minutes": 25,
            "streak_opt_in": False,
            "onboarding_completed": True,
        },
    )
    assert pref_res.status_code == 200
    u_prefs = pref_res.json()["user"]["preferences"]
    assert u_prefs["language"] == "bilingual"
    assert u_prefs["text_size"] == "large"
    assert u_prefs["reduced_motion"] is True
    assert u_prefs["plain_language_mode"] is True

    # Request progressive hints from curated content
    next_q = client.get("/api/questions/next", headers=student_headers).json()[
        "question"
    ]
    h0 = client.get(
        f"/api/questions/{next_q['id']}/hint?hint_index=0",
        headers=student_headers,
    )
    assert h0.status_code == 200
    assert h0.json()["hint_index"] == 0
    assert h0.json()["source"] == "curated_content"

    # Privacy export
    exp_res = client.get("/api/auth/export-my-data", headers=student_headers)
    assert exp_res.status_code == 200
    assert "privacy_notice" in exp_res.json()
    assert len(exp_res.json()["mastery_states"]) >= 6

    # Educator acknowledges an intervention outcome
    analytics = client.get(
        "/api/educator/classes/1/analytics", headers=educator_headers
    ).json()
    first_outcome_id = analytics["intervention_outcomes"][0]["id"]
    ack_res = client.post(
        "/api/educator/classes/1/acknowledge",
        headers=educator_headers,
        json={
            "outcome_id": first_outcome_id,
            "educator_note": "Reviewed with learner during lab session.",
            "acknowledged": True,
        },
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["educator_acknowledged"] is True

