from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import (
    Achievement,
    Activity,
    AnswerOption,
    Attempt,
    Concept,
    ConceptPrerequisite,
    Course,
    Diagnosis,
    InterventionOutcome,
    LearnerPreference,
    MasteryState,
    Misconception,
    Question,
    Recommendation,
    User,
    UserAchievement,
)
from app.schemas.api_schemas import (
    AttemptSubmitRequest,
    DiagnosticFollowupSubmitRequest,
    InterventionCompleteRequest,
    InterventionVerifyRequest,
)
from app.services.audit import log_audit_event
from app.services.diagnosis import diagnose_attempt, resolve_diagnostic_followup
from app.services.gamification import award_points_and_check_achievements
from app.services.mastery import (
    get_or_create_mastery_state,
    mastery_band_label,
    update_concept_mastery,
)
from app.services.recommendation import (
    compute_prerequisite_maps,
    generate_recommendations_for_user,
)
from app.services.tutor import get_hint_for_question, tutor_adapter

router = APIRouter(prefix="/api", tags=["learning"])


def serialize_question_for_learner(question: Question, concept: Optional[Concept] = None) -> dict:
    """Serializes a question for presentation without exposing the answer key."""
    return {
        "id": question.id,
        "stable_id": question.stable_id,
        "concept_id": question.concept_id,
        "concept_name": concept.name if concept else (question.concept.name if question.concept else ""),
        "difficulty": question.difficulty,
        "difficulty_label": {1: "Foundational", 2: "Intermediate", 3: "Applied"}
        .get(question.difficulty, "Foundational"),
        "question_type": question.question_type,
        "is_verification_only": question.is_verification_only,
        "is_diagnostic_followup": question.is_diagnostic_followup,
        "content": question.content,
        "code_snippet": question.code_snippet,
        "diagram_svg": question.diagram_svg,
        "audio_transcript": question.audio_transcript,
        "total_hints": len(question.hint_ladder or []),
        "version": question.version,
        "options": [
            {
                "id": opt.id,
                "option_key": opt.option_key,
                "option_text": opt.option_text,
            }
            for opt in sorted(question.answer_options, key=lambda o: o.option_key)
        ],
    }


def serialize_activity(activity: Activity, concept: Optional[Concept] = None, misc: Optional[Misconception] = None) -> dict:
    return {
        "id": activity.id,
        "stable_id": activity.stable_id,
        "concept_id": activity.concept_id,
        "concept_name": concept.name if concept else (activity.concept.name if activity.concept else ""),
        "target_misconception_id": activity.target_misconception_id,
        "target_misconception_label": misc.label if misc else None,
        "title": activity.title,
        "activity_type": activity.activity_type,
        "difficulty": activity.difficulty,
        "content_ref": activity.content_ref,
        "content_body": activity.content_body,
        "plain_language_body": activity.plain_language_body or activity.content_body,
        "code_example": activity.code_example,
        "diagram_svg": activity.diagram_svg,
        "audio_transcript": activity.audio_transcript,
        "interactive_exercise": activity.interactive_exercise,
        "format": activity.format,
        "estimated_duration": activity.estimated_duration,
        "version": activity.version,
    }


def check_answer_correctness(question: Question, raw_response: str) -> bool:
    resp = (raw_response or "").strip()
    key = (question.answer_key or "").strip()
    if resp.upper() == key.upper():
        return True
    # Also allow matching the full text of the correct option if the learner submitted text
    for opt in question.answer_options:
        if opt.is_correct and (
            opt.option_key.strip().upper() == resp.upper()
            or opt.option_text.strip().lower() == resp.lower()
        ):
            return True
    return False


@router.get("/courses")
def list_courses(db: Session = Depends(get_db)):
    courses = (
        db.query(Course)
        .filter(Course.status == "published")
        .order_by(Course.id.asc())
        .all()
    )
    return {
        "courses": [
            {
                "id": c.id,
                "slug": c.slug,
                "title": c.title,
                "description": c.description,
                "status": c.status,
                "version": c.version,
                "concepts_count": len([con for con in c.concepts if con.status == "published"]),
            }
            for c in courses
        ]
    }


@router.get("/courses/{course_id}/concepts")
def list_course_concepts(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    concepts = (
        db.query(Concept)
        .filter(Concept.course_id == course_id, Concept.status == "published")
        .order_by(Concept.order_index.asc(), Concept.id.asc())
        .all()
    )
    prereqs_of, dependents_of = compute_prerequisite_maps(db, course_id=course_id)

    mastery_map: dict[int, MasteryState] = {}
    for c in concepts:
        ms = get_or_create_mastery_state(db, current_user.id, c)
        mastery_map[c.id] = ms
    db.commit()

    concept_items = []
    for c in concepts:
        ms = mastery_map[c.id]
        prereq_ids = prereqs_of.get(c.id, [])
        unmet = [
            pid
            for pid in prereq_ids
            if (mastery_map.get(pid).mastery if pid in mastery_map else 0.35) < 0.45
        ]
        concept_items.append(
            {
                "id": c.id,
                "course_id": c.course_id,
                "slug": c.slug,
                "name": c.name,
                "description": c.description,
                "learning_objective": c.learning_objective,
                "order_index": c.order_index,
                "prerequisite_ids": prereq_ids,
                "dependent_ids": dependents_of.get(c.id, []),
                "prerequisites_ready": len(unmet) == 0,
                "mastery": round(ms.mastery, 3),
                "mastery_percent": int(round(ms.mastery * 100)),
                "attempts_count": ms.attempts_count,
                "correct_count": ms.correct_count,
                "uncertainty": ms.uncertainty,
                "status_label": mastery_band_label(ms.mastery, ms.attempts_count),
                "evidence_note": ms.uncertainty_or_evidence,
                "questions_count": len([q for q in c.questions if q.status == "published" and not q.is_diagnostic_followup]),
            }
        )

    edges = [
        {"from_prerequisite_id": p_id, "to_concept_id": c.id}
        for c in concepts
        for p_id in prereqs_of.get(c.id, [])
    ]

    return {
        "course": {
            "id": course.id,
            "slug": course.slug,
            "title": course.title,
            "description": course.description,
            "version": course.version,
        },
        "concepts": concept_items,
        "prerequisite_edges": edges,
        "model_disclaimer": (
            "Mastery values are heuristic estimates in [0, 1] updated from observed responses "
            "(M_new = (1 - alpha)*M_old + alpha*y). They guide practice selection and are not definitive "
            "measures of ability."
        ),
    }


@router.get("/questions/next")
def get_next_question(
    concept_id: Optional[int] = Query(default=None),
    exclude_question_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adaptive question selector (SRC-1, FR-05, FR-07):
    - Chooses target concept (either requested concept_id or highest-priority prerequisite-ready concept).
    - Adapts question difficulty (1..3) to the learner's current mastery estimate for that concept.
    - Avoids repeating the most recently answered question when alternatives exist.
    """
    concepts = (
        db.query(Concept)
        .filter(Concept.status == "published")
        .order_by(Concept.order_index.asc())
        .all()
    )
    if not concepts:
        raise HTTPException(status_code=404, detail="No published concepts available.")

    mastery_map = {
        c.id: get_or_create_mastery_state(db, current_user.id, c)
        for c in concepts
    }
    db.commit()

    target_concept: Optional[Concept] = None
    if concept_id is not None:
        target_concept = next((c for c in concepts if c.id == concept_id), None)
        if not target_concept:
            raise HTTPException(status_code=404, detail="Requested concept not found.")
    else:
        prereqs_of, _ = compute_prerequisite_maps(db)
        eligible = []
        for c in concepts:
            m_val = mastery_map[c.id].mastery
            p_ids = prereqs_of.get(c.id, [])
            prereqs_met = all(
                mastery_map.get(pid, mastery_map[c.id]).mastery >= 0.45
                for pid in p_ids
            )
            eligible.append((prereqs_met, m_val < 0.80, -m_val, -c.order_index, c))
        eligible.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)
        target_concept = eligible[0][4]

    ms = mastery_map[target_concept.id]
    if ms.attempts_count == 0 or ms.mastery <= 0.45:
        target_difficulty = 1
    elif ms.mastery < 0.72:
        target_difficulty = 2
    else:
        target_difficulty = 3

    recent_attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.submitted_at.desc())
        .limit(5)
        .all()
    )
    recent_q_ids = {a.question_id for a in recent_attempts}
    if exclude_question_id:
        recent_q_ids.add(exclude_question_id)

    candidate_questions = (
        db.query(Question)
        .filter(
            Question.concept_id == target_concept.id,
            Question.status == "published",
            Question.is_diagnostic_followup == False,  # noqa: E712
            Question.is_verification_only == False,  # noqa: E712
        )
        .all()
    )
    if not candidate_questions:
        # Fallback to any published non-followup question in the course
        candidate_questions = (
            db.query(Question)
            .filter(
                Question.status == "published",
                Question.is_diagnostic_followup == False,  # noqa: E712
            )
            .all()
        )
    if not candidate_questions:
        raise HTTPException(status_code=404, detail="No published questions available.")

    # Rank questions: prefer not recently attempted, then closest difficulty to target_difficulty
    candidate_questions.sort(
        key=lambda q: (
            q.id in recent_q_ids,
            abs((q.difficulty or 1) - target_difficulty),
            q.id,
        )
    )
    chosen = candidate_questions[0]

    return {
        "question": serialize_question_for_learner(chosen, target_concept),
        "adaptive_selection_reason": (
            f"Selected for concept '{target_concept.name}' (current mastery estimate "
            f"{int(round(ms.mastery * 100))}%, target difficulty Level {target_difficulty})."
        ),
        "concept_mastery": {
            "concept_id": target_concept.id,
            "concept_name": target_concept.name,
            "mastery": round(ms.mastery, 3),
            "status_label": mastery_band_label(ms.mastery, ms.attempts_count),
        },
    }


@router.get("/questions/{question_id}/hint")
def request_question_hint(
    question_id: int,
    hint_index: int = Query(default=0, ge=0, le=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    hint_payload = get_hint_for_question(question, hint_index=hint_index)
    log_audit_event(
        db,
        action="hint_requested",
        entity_type="question",
        entity_id=question.stable_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={"hint_index": hint_index},
    )
    db.commit()
    return hint_payload


@router.post("/attempts")
def submit_attempt(
    payload: AttemptSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    concept = db.query(Concept).filter(Concept.id == question.concept_id).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Question concept not found.")

    is_correct = check_answer_correctness(question, payload.response)

    attempt = Attempt(
        user_id=current_user.id,
        question_id=question.id,
        response=payload.response.strip(),
        is_correct=is_correct,
        hints_used=payload.hints_used,
        attempt_context=payload.attempt_context or "practice",
    )
    db.add(attempt)
    db.flush()

    # Update ONLY the concept measured by this question
    prev_mastery, updated_mastery = update_concept_mastery(
        db,
        user_id=current_user.id,
        concept=concept,
        is_correct=is_correct,
        context_note=f"question {question.stable_id}",
    )

    # Run transparent misconception rule engine
    diagnosis = diagnose_attempt(db, attempt=attempt, question=question)

    misconception_obj: Optional[Misconception] = None
    if diagnosis.misconception_id:
        misconception_obj = (
            db.query(Misconception)
            .filter(Misconception.id == diagnosis.misconception_id)
            .first()
        )

    followup_question_payload = None
    if (
        diagnosis.status == "ambiguous_followup_needed"
        and diagnosis.followup_question_id
    ):
        fq = (
            db.query(Question)
            .filter(Question.id == diagnosis.followup_question_id)
            .first()
        )
        if fq:
            followup_question_payload = serialize_question_for_learner(fq, concept)

    prefs = (
        db.query(LearnerPreference)
        .filter(LearnerPreference.user_id == current_user.id)
        .first()
    )
    plain_mode = bool(prefs and prefs.plain_language_mode)
    tutor_feedback = tutor_adapter.build_grounded_tutor_response(
        question=question,
        misconception=misconception_obj,
        plain_language=plain_mode,
    )

    # Generate updated explainable recommendations
    recs = generate_recommendations_for_user(
        db,
        user_id=current_user.id,
        strategy="proposed",
        limit=4,
        trigger_attempt_id=attempt.id,
        trigger_diagnosis_id=diagnosis.id,
    )

    newly_earned = award_points_and_check_achievements(
        db,
        user=current_user,
        event_type="attempt",
        is_correct=is_correct,
    )

    log_audit_event(
        db,
        action="attempt_and_diagnosis_recorded",
        entity_type="attempt",
        entity_id=str(attempt.id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        rule_version=diagnosis.rule_version,
        metadata={
            "question_stable_id": question.stable_id,
            "concept_id": concept.id,
            "is_correct": is_correct,
            "mastery_before": prev_mastery,
            "mastery_after": updated_mastery.mastery,
            "diagnosis_status": diagnosis.status,
            "diagnosis_confidence": diagnosis.confidence,
            "misconception_code": misconception_obj.code if misconception_obj else None,
        },
    )
    db.commit()

    top_rec_payload = None
    if recs:
        top_r = recs[0]
        top_act = db.query(Activity).filter(Activity.id == top_r.activity_id).first()
        if top_act:
            top_rec_payload = {
                "recommendation_id": top_r.id,
                "total_score": top_r.total_score,
                "score_components": top_r.score_components,
                "reason": top_r.reason,
                "rule_version": top_r.rule_version,
                "activity": serialize_activity(top_act, concept, misconception_obj),
            }

    return {
        "attempt_id": attempt.id,
        "question_id": question.id,
        "stable_id": question.stable_id,
        "submitted_response": attempt.response,
        "is_correct": is_correct,
        "status_badge": "Correct response" if is_correct else "Needs review — let's inspect why",
        "mastery_update": {
            "concept_id": concept.id,
            "concept_name": concept.name,
            "previous_mastery": round(prev_mastery, 3),
            "new_mastery": round(updated_mastery.mastery, 3),
            "alpha": updated_mastery.last_alpha,
            "attempts_count": updated_mastery.attempts_count,
            "uncertainty": updated_mastery.uncertainty,
            "evidence_note": updated_mastery.uncertainty_or_evidence,
            "model_version": updated_mastery.model_version,
        },
        "diagnosis": {
            "id": diagnosis.id,
            "status": diagnosis.status,
            "confidence": diagnosis.confidence,
            "evidence": diagnosis.evidence,
            "rule_version": diagnosis.rule_version,
            "misconception": (
                {
                    "id": misconception_obj.id,
                    "code": misconception_obj.code,
                    "label": misconception_obj.label,
                    "description": misconception_obj.description,
                }
                if misconception_obj
                else None
            ),
            "candidate_misconceptions": diagnosis.candidate_misconceptions or [],
            "requires_diagnostic_followup": followup_question_payload is not None,
            "followup_question": followup_question_payload,
        },
        "tutor": tutor_feedback,
        "recommended_next": top_rec_payload,
        "gamification": {
            "total_points": current_user.points,
            "current_streak": current_user.current_streak,
            "newly_earned_achievements": newly_earned,
        },
    }


@router.post("/attempts/{attempt_id}/diagnostic-follow-up")
def submit_diagnostic_followup(
    attempt_id: int,
    payload: DiagnosticFollowupSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    original_attempt = (
        db.query(Attempt)
        .filter(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
        .first()
    )
    if not original_attempt:
        raise HTTPException(status_code=404, detail="Original attempt not found.")

    diagnosis = (
        db.query(Diagnosis)
        .filter(Diagnosis.attempt_id == original_attempt.id)
        .order_by(Diagnosis.id.desc())
        .first()
    )
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis record not found.")

    followup_q = (
        db.query(Question)
        .filter(Question.id == payload.followup_question_id)
        .first()
    )
    if not followup_q:
        raise HTTPException(status_code=404, detail="Diagnostic follow-up question not found.")

    concept = db.query(Concept).filter(Concept.id == followup_q.concept_id).first()
    is_correct = check_answer_correctness(followup_q, payload.response)

    followup_attempt = Attempt(
        user_id=current_user.id,
        question_id=followup_q.id,
        response=payload.response.strip(),
        is_correct=is_correct,
        hints_used=0,
        attempt_context="diagnostic_followup",
    )
    db.add(followup_attempt)
    db.flush()

    updated_diag = resolve_diagnostic_followup(
        db,
        diagnosis=diagnosis,
        followup_question=followup_q,
        followup_attempt=followup_attempt,
    )

    # Gentle mastery update (alpha=0.12) from the short diagnostic probe
    prev_m, updated_ms = update_concept_mastery(
        db,
        user_id=current_user.id,
        concept=concept,
        is_correct=is_correct,
        alpha=0.12,
        context_note=f"diagnostic follow-up {followup_q.stable_id}",
    )

    confirmed_misc = None
    if updated_diag.misconception_id:
        confirmed_misc = (
            db.query(Misconception)
            .filter(Misconception.id == updated_diag.misconception_id)
            .first()
        )

    recs = generate_recommendations_for_user(
        db,
        user_id=current_user.id,
        strategy="proposed",
        limit=4,
        trigger_attempt_id=original_attempt.id,
        trigger_diagnosis_id=updated_diag.id,
    )

    newly_earned = award_points_and_check_achievements(
        db,
        user=current_user,
        event_type="diagnostic_followup",
        is_correct=is_correct,
    )

    log_audit_event(
        db,
        action="diagnostic_followup_resolved",
        entity_type="diagnosis",
        entity_id=str(updated_diag.id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        rule_version=updated_diag.rule_version,
        metadata={
            "original_attempt_id": original_attempt.id,
            "followup_question_stable_id": followup_q.stable_id,
            "followup_is_correct": is_correct,
            "resolved_status": updated_diag.status,
            "confirmed_misconception": confirmed_misc.code if confirmed_misc else None,
            "updated_confidence": updated_diag.confidence,
        },
    )
    db.commit()

    top_rec_payload = None
    if recs:
        top_r = recs[0]
        top_act = db.query(Activity).filter(Activity.id == top_r.activity_id).first()
        if top_act:
            top_rec_payload = {
                "recommendation_id": top_r.id,
                "total_score": top_r.total_score,
                "score_components": top_r.score_components,
                "reason": top_r.reason,
                "rule_version": top_r.rule_version,
                "activity": serialize_activity(top_act, concept, confirmed_misc),
            }

    return {
        "followup_attempt_id": followup_attempt.id,
        "is_correct": is_correct,
        "followup_explanation": followup_q.explanation,
        "authoritative_answer_key": followup_q.answer_key,
        "diagnosis": {
            "id": updated_diag.id,
            "status": updated_diag.status,
            "confidence": updated_diag.confidence,
            "evidence": updated_diag.evidence,
            "rule_version": updated_diag.rule_version,
            "misconception": (
                {
                    "id": confirmed_misc.id,
                    "code": confirmed_misc.code,
                    "label": confirmed_misc.label,
                    "description": confirmed_misc.description,
                }
                if confirmed_misc
                else None
            ),
            "candidate_misconceptions": updated_diag.candidate_misconceptions or [],
        },
        "mastery_update": {
            "concept_id": concept.id,
            "concept_name": concept.name,
            "previous_mastery": round(prev_m, 3),
            "new_mastery": round(updated_ms.mastery, 3),
        },
        "recommended_next": top_rec_payload,
        "gamification": {
            "total_points": current_user.points,
            "newly_earned_achievements": newly_earned,
        },
    }


@router.get("/recommendations")
def get_recommendations(
    strategy: str = Query(default="proposed", pattern="^(proposed|baseline_score)$"),
    refresh: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if refresh:
        recs = generate_recommendations_for_user(
            db, user_id=current_user.id, strategy=strategy, limit=5
        )
        db.commit()
    else:
        recs = (
            db.query(Recommendation)
            .filter(
                Recommendation.user_id == current_user.id,
                Recommendation.strategy == strategy,
                Recommendation.status.in_(["pending", "in_progress"]),
            )
            .order_by(Recommendation.rank.asc())
            .all()
        )
        if not recs:
            recs = generate_recommendations_for_user(
                db, user_id=current_user.id, strategy=strategy, limit=5
            )
            db.commit()

    items = []
    for r in recs:
        act = db.query(Activity).filter(Activity.id == r.activity_id).first()
        concept = db.query(Concept).filter(Concept.id == r.concept_id).first()
        misc = (
            db.query(Misconception)
            .filter(Misconception.id == act.target_misconception_id)
            .first()
            if (act and act.target_misconception_id)
            else None
        )
        if not act or not concept:
            continue
        items.append(
            {
                "id": r.id,
                "rank": r.rank,
                "strategy": r.strategy,
                "status": r.status,
                "total_score": r.total_score,
                "score_components": r.score_components,
                "reason": r.reason,
                "rule_version": r.rule_version,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "activity": serialize_activity(act, concept, misc),
            }
        )

    return {
        "strategy": strategy,
        "provisional_weights_note": (
            "Score formula R(a) = 0.50*gap_relevance + 0.30*prerequisite_importance + 0.20*difficulty_fit "
            "uses provisional configurable weights normalized to [0, 1]."
        ),
        "recommendations": items,
    }


@router.post("/interventions/{recommendation_id}/complete")
def complete_intervention(
    recommendation_id: int,
    payload: InterventionCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = (
        db.query(Recommendation)
        .filter(
            Recommendation.id == recommendation_id,
            Recommendation.user_id == current_user.id,
        )
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    concept = db.query(Concept).filter(Concept.id == rec.concept_id).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found.")

    rec.status = "completed"
    rec.completed_at = datetime.now(timezone.utc)

    # Identify pre-intervention question to guarantee the verification question is FRESH (different surface item)
    exclude_q_ids = set()
    if rec.trigger_attempt_id:
        pre_att = db.query(Attempt).filter(Attempt.id == rec.trigger_attempt_id).first()
        if pre_att:
            exclude_q_ids.add(pre_att.question_id)

    recent_atts = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.submitted_at.desc())
        .limit(3)
        .all()
    )
    for ra in recent_atts:
        exclude_q_ids.add(ra.question_id)

    # Prefer dedicated verification questions for this concept, then any other question for this concept
    verif_candidates = (
        db.query(Question)
        .filter(
            Question.concept_id == concept.id,
            Question.status == "published",
            Question.is_diagnostic_followup == False,  # noqa: E712
        )
        .all()
    )
    if not verif_candidates:
        raise HTTPException(
            status_code=404,
            detail="No verification questions found for this concept.",
        )

    verif_candidates.sort(
        key=lambda q: (
            q.id in exclude_q_ids,
            not q.is_verification_only,
            q.id,
        )
    )
    fresh_question = verif_candidates[0]

    newly_earned = award_points_and_check_achievements(
        db,
        user=current_user,
        event_type="intervention_complete",
        is_correct=True,
    )

    log_audit_event(
        db,
        action="intervention_completed",
        entity_type="recommendation",
        entity_id=str(rec.id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        rule_version=rec.rule_version,
        metadata={
            "activity_id": rec.activity_id,
            "concept_id": concept.id,
            "completion_seconds": payload.completion_seconds,
            "assigned_verification_question": fresh_question.stable_id,
        },
    )
    db.commit()

    return {
        "recommendation_id": rec.id,
        "status": rec.status,
        "verification_question": serialize_question_for_learner(fresh_question, concept),
        "verification_note": (
            f"Fresh verification check ({fresh_question.stable_id}) selected for '{concept.name}' "
            f"to test immediate post-remediation understanding."
        ),
        "gamification": {
            "total_points": current_user.points,
            "newly_earned_achievements": newly_earned,
        },
    }


@router.post("/interventions/{recommendation_id}/verify")
def verify_intervention(
    recommendation_id: int,
    payload: InterventionVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = (
        db.query(Recommendation)
        .filter(
            Recommendation.id == recommendation_id,
            Recommendation.user_id == current_user.id,
        )
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    verif_q = (
        db.query(Question)
        .filter(Question.id == payload.verification_question_id)
        .first()
    )
    if not verif_q:
        raise HTTPException(status_code=404, detail="Verification question not found.")

    concept = db.query(Concept).filter(Concept.id == verif_q.concept_id).first()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found.")

    is_correct = check_answer_correctness(verif_q, payload.response)

    verif_attempt = Attempt(
        user_id=current_user.id,
        question_id=verif_q.id,
        response=payload.response.strip(),
        is_correct=is_correct,
        hints_used=0,
        attempt_context="verification",
    )
    db.add(verif_attempt)
    db.flush()

    verif_diag = diagnose_attempt(db, attempt=verif_attempt, question=verif_q)

    # Check if the original misconception recurred
    original_misc_id: Optional[int] = None
    if rec.trigger_diagnosis_id:
        orig_diag = (
            db.query(Diagnosis)
            .filter(Diagnosis.id == rec.trigger_diagnosis_id)
            .first()
        )
        if orig_diag:
            original_misc_id = orig_diag.misconception_id

    act = db.query(Activity).filter(Activity.id == rec.activity_id).first()
    if not original_misc_id and act and act.target_misconception_id:
        original_misc_id = act.target_misconception_id

    error_recurred = False
    if not is_correct:
        if (
            original_misc_id is not None
            and verif_diag.misconception_id is not None
            and verif_diag.misconception_id == original_misc_id
        ):
            error_recurred = True
        elif original_misc_id is None:
            error_recurred = True

    pre_mastery, updated_ms = update_concept_mastery(
        db,
        user_id=current_user.id,
        concept=concept,
        is_correct=is_correct,
        context_note=f"post-intervention verification {verif_q.stable_id}",
    )

    immediate_outcome = "improved" if is_correct else "still_practicing"
    rec.status = "verified"

    outcome = InterventionOutcome(
        recommendation_id=rec.id,
        user_id=current_user.id,
        concept_id=concept.id,
        pre_attempt_id=rec.trigger_attempt_id,
        followup_attempt_id=verif_attempt.id,
        verification_question_id=verif_q.id,
        pre_mastery=pre_mastery,
        post_mastery=updated_ms.mastery,
        immediate_outcome=immediate_outcome,
        error_recurred=error_recurred,
        original_misconception_id=original_misc_id,
        post_misconception_id=verif_diag.misconception_id,
        completion_seconds=payload.completion_seconds,
        rule_version=settings.RULE_ENGINE_VERSION,
    )
    db.add(outcome)
    db.flush()

    # Refresh recommendations after verification
    generate_recommendations_for_user(
        db, user_id=current_user.id, strategy="proposed", limit=4
    )

    newly_earned = award_points_and_check_achievements(
        db,
        user=current_user,
        event_type="verification_complete",
        is_correct=is_correct,
    )

    log_audit_event(
        db,
        action="intervention_verified",
        entity_type="intervention_outcome",
        entity_id=str(outcome.id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        rule_version=outcome.rule_version,
        metadata={
            "recommendation_id": rec.id,
            "verification_question": verif_q.stable_id,
            "is_correct": is_correct,
            "error_recurred": error_recurred,
            "pre_mastery": pre_mastery,
            "post_mastery": updated_ms.mastery,
            "immediate_outcome": immediate_outcome,
        },
    )
    db.commit()

    return {
        "outcome_id": outcome.id,
        "recommendation_id": rec.id,
        "verification_attempt_id": verif_attempt.id,
        "is_correct": is_correct,
        "immediate_outcome": immediate_outcome,
        "error_recurred": error_recurred,
        "authoritative_answer_key": verif_q.answer_key,
        "explanation": verif_q.explanation,
        "mastery_update": {
            "concept_id": concept.id,
            "concept_name": concept.name,
            "pre_mastery": round(pre_mastery, 3),
            "post_mastery": round(updated_ms.mastery, 3),
            "status_label": mastery_band_label(
                updated_ms.mastery, updated_ms.attempts_count
            ),
            "evidence_note": updated_ms.uncertainty_or_evidence,
        },
        "retention_disclaimer": (
            "This result is recorded as immediate post-intervention verification evidence. "
            "A single immediate follow-up does not prove durable long-term retention."
        ),
        "gamification": {
            "total_points": current_user.points,
            "newly_earned_achievements": newly_earned,
        },
    }


@router.get("/progress/summary")
def get_progress_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    concepts = (
        db.query(Concept)
        .filter(Concept.status == "published")
        .order_by(Concept.order_index.asc())
        .all()
    )
    concept_summaries = []
    strengths = []
    practice_needs = []

    for c in concepts:
        ms = get_or_create_mastery_state(db, current_user.id, c)
        item = {
            "concept_id": c.id,
            "slug": c.slug,
            "name": c.name,
            "order_index": c.order_index,
            "mastery": round(ms.mastery, 3),
            "mastery_percent": int(round(ms.mastery * 100)),
            "attempts_count": ms.attempts_count,
            "correct_count": ms.correct_count,
            "uncertainty": ms.uncertainty,
            "status_label": mastery_band_label(ms.mastery, ms.attempts_count),
            "evidence_note": ms.uncertainty_or_evidence,
        }
        concept_summaries.append(item)
        if ms.attempts_count > 0 and ms.mastery >= 0.65:
            strengths.append(item)
        elif ms.mastery < 0.55 or ms.attempts_count == 0:
            practice_needs.append(item)

    db.commit()

    recent_attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.submitted_at.desc())
        .limit(12)
        .all()
    )
    question_lookup = {
        q.id: q for q in db.query(Question).all()
    }
    concept_lookup = {c.id: c for c in concepts}
    misc_lookup = {m.id: m for m in db.query(Misconception).all()}

    recent_diagnoses = (
        db.query(Diagnosis)
        .filter(Diagnosis.user_id == current_user.id)
        .order_by(Diagnosis.created_at.desc())
        .limit(10)
        .all()
    )

    outcomes = (
        db.query(InterventionOutcome)
        .filter(InterventionOutcome.user_id == current_user.id)
        .order_by(InterventionOutcome.created_at.desc())
        .limit(10)
        .all()
    )

    all_achievements = db.query(Achievement).all()
    earned_map = {
        ua.achievement_id: ua.earned_at
        for ua in db.query(UserAchievement)
        .filter(UserAchievement.user_id == current_user.id)
        .all()
    }

    overall_mastery = (
        round(
            sum(c["mastery"] for c in concept_summaries) / len(concept_summaries),
            3,
        )
        if concept_summaries
        else 0.0
    )

    return {
        "overall_mastery_estimate": overall_mastery,
        "overall_mastery_percent": int(round(overall_mastery * 100)),
        "total_attempts": db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .count(),
        "verified_interventions_count": len(outcomes),
        "gamification": {
            "points": current_user.points,
            "current_streak": current_user.current_streak,
            "daily_goal_minutes": current_user.daily_goal_minutes,
            "streak_opt_in": current_user.streak_opt_in,
            "earning_rules": [
                {"action": "Complete a question attempt", "points": "5 pts (effort) + 10 pts (correct)"},
                {"action": "Answer a diagnostic follow-up", "points": "10 pts"},
                {"action": "Complete a targeted learning intervention", "points": "20 pts"},
                {"action": "Complete post-intervention verification", "points": "10–25 pts"},
            ],
            "achievements": [
                {
                    "id": ach.id,
                    "code": ach.code,
                    "name": ach.name,
                    "description": ach.description,
                    "category": ach.category,
                    "points_reward": ach.points_reward,
                    "earned": ach.id in earned_map,
                    "earned_at": (
                        earned_map[ach.id].isoformat()
                        if ach.id in earned_map and earned_map[ach.id]
                        else None
                    ),
                }
                for ach in all_achievements
            ],
        },
        "concepts": concept_summaries,
        "strengths": strengths,
        "practice_needs": practice_needs,
        "recent_attempts": [
            {
                "id": a.id,
                "question_stable_id": (
                    question_lookup[a.question_id].stable_id
                    if a.question_id in question_lookup
                    else f"Q-{a.question_id}"
                ),
                "concept_name": (
                    concept_lookup[question_lookup[a.question_id].concept_id].name
                    if (
                        a.question_id in question_lookup
                        and question_lookup[a.question_id].concept_id in concept_lookup
                    )
                    else "Python"
                ),
                "response": a.response,
                "is_correct": a.is_correct,
                "attempt_context": a.attempt_context,
                "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            }
            for a in recent_attempts
        ],
        "recent_diagnoses": [
            {
                "id": d.id,
                "concept_name": (
                    concept_lookup[d.concept_id].name
                    if d.concept_id in concept_lookup
                    else "Python"
                ),
                "status": d.status,
                "confidence": d.confidence,
                "evidence": d.evidence,
                "misconception_label": (
                    misc_lookup[d.misconception_id].label
                    if d.misconception_id and d.misconception_id in misc_lookup
                    else None
                ),
                "rule_version": d.rule_version,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in recent_diagnoses
        ],
        "intervention_history": [
            {
                "id": o.id,
                "recommendation_id": o.recommendation_id,
                "concept_name": (
                    concept_lookup[o.concept_id].name
                    if o.concept_id in concept_lookup
                    else "Python"
                ),
                "pre_mastery": round(o.pre_mastery, 3),
                "post_mastery": round(o.post_mastery, 3),
                "immediate_outcome": o.immediate_outcome,
                "error_recurred": o.error_recurred,
                "completion_seconds": o.completion_seconds,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in outcomes
        ],
    }
