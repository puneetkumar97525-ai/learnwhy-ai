from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.entities import (
    Activity,
    AnswerOption,
    AuditEvent,
    Concept,
    ConceptPrerequisite,
    Course,
    Misconception,
    Question,
    User,
)
from app.schemas.api_schemas import (
    AdminActivityCreateRequest,
    AdminConceptCreateRequest,
    AdminMisconceptionCreateRequest,
    AdminQuestionCreateRequest,
    AdminQuestionUpdateRequest,
)
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/overview")
def get_admin_overview(
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    courses = db.query(Course).all()
    concepts = db.query(Concept).order_by(Concept.order_index.asc()).all()
    prereqs = db.query(ConceptPrerequisite).all()
    questions = db.query(Question).order_by(Question.id.asc()).all()
    misconceptions = db.query(Misconception).order_by(Misconception.id.asc()).all()
    activities = db.query(Activity).order_by(Activity.id.asc()).all()
    audit_logs = (
        db.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(40)
        .all()
    )

    concept_map = {c.id: c.name for c in concepts}
    prereq_map: dict[int, list[int]] = {}
    for p in prereqs:
        prereq_map.setdefault(p.concept_id, []).append(p.prerequisite_id)

    return {
        "courses": [
            {
                "id": c.id,
                "slug": c.slug,
                "title": c.title,
                "status": c.status,
                "version": c.version,
            }
            for c in courses
        ],
        "concepts": [
            {
                "id": c.id,
                "course_id": c.course_id,
                "slug": c.slug,
                "name": c.name,
                "description": c.description,
                "learning_objective": c.learning_objective,
                "order_index": c.order_index,
                "prior_mastery": c.prior_mastery,
                "status": c.status,
                "prerequisite_ids": prereq_map.get(c.id, []),
            }
            for c in concepts
        ],
        "questions": [
            {
                "id": q.id,
                "stable_id": q.stable_id,
                "concept_id": q.concept_id,
                "concept_name": concept_map.get(q.concept_id, ""),
                "difficulty": q.difficulty,
                "question_type": q.question_type,
                "is_verification_only": q.is_verification_only,
                "is_diagnostic_followup": q.is_diagnostic_followup,
                "content": q.content,
                "code_snippet": q.code_snippet,
                "answer_key": q.answer_key,
                "explanation": q.explanation,
                "version": q.version,
                "status": q.status,
                "options": [
                    {
                        "id": o.id,
                        "option_key": o.option_key,
                        "option_text": o.option_text,
                        "misconception_id": o.misconception_id,
                        "secondary_misconception_id": o.secondary_misconception_id,
                        "confidence_weight": o.confidence_weight,
                        "is_correct": o.is_correct,
                    }
                    for o in q.answer_options
                ],
            }
            for q in questions
        ],
        "misconceptions": [
            {
                "id": m.id,
                "code": m.code,
                "concept_id": m.concept_id,
                "concept_name": concept_map.get(m.concept_id, ""),
                "label": m.label,
                "description": m.description,
                "diagnostic_rule": m.diagnostic_rule,
                "remediation_focus": m.remediation_focus,
                "rule_version": m.rule_version,
                "status": m.status,
            }
            for m in misconceptions
        ],
        "activities": [
            {
                "id": a.id,
                "stable_id": a.stable_id,
                "concept_id": a.concept_id,
                "concept_name": concept_map.get(a.concept_id, ""),
                "target_misconception_id": a.target_misconception_id,
                "title": a.title,
                "activity_type": a.activity_type,
                "difficulty": a.difficulty,
                "format": a.format,
                "estimated_duration": a.estimated_duration,
                "version": a.version,
                "status": a.status,
            }
            for a in activities
        ],
        "audit_events": [
            {
                "id": e.id,
                "actor_id": e.actor_id,
                "actor_role": e.actor_role,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "rule_version": e.rule_version,
                "metadata": e.metadata_json,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in audit_logs
        ],
    }


@router.post("/concepts", status_code=status.HTTP_201_CREATED)
def create_concept(
    payload: AdminConceptCreateRequest,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    existing = db.query(Concept).filter(Concept.slug == payload.slug).first()
    if existing:
        raise HTTPException(
            status_code=409, detail="A concept with this slug already exists."
        )

    concept = Concept(
        course_id=payload.course_id,
        slug=payload.slug.strip(),
        name=payload.name.strip(),
        description=payload.description.strip(),
        learning_objective=payload.learning_objective.strip(),
        order_index=payload.order_index,
        prior_mastery=payload.prior_mastery,
        status="published",
    )
    db.add(concept)
    db.flush()

    for pid in set(payload.prerequisite_ids):
        if pid != concept.id:
            db.add(
                ConceptPrerequisite(concept_id=concept.id, prerequisite_id=pid)
            )

    log_audit_event(
        db,
        action="admin_concept_created",
        entity_type="concept",
        entity_id=str(concept.id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={"slug": concept.slug, "prerequisites": payload.prerequisite_ids},
    )
    db.commit()
    db.refresh(concept)
    return {"id": concept.id, "slug": concept.slug, "name": concept.name}


@router.post("/questions", status_code=status.HTTP_201_CREATED)
def create_question(
    payload: AdminQuestionCreateRequest,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Question)
        .filter(Question.stable_id == payload.stable_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A question with this stable_id already exists.",
        )

    question = Question(
        stable_id=payload.stable_id.strip(),
        concept_id=payload.concept_id,
        difficulty=payload.difficulty,
        question_type=payload.question_type,
        is_verification_only=payload.is_verification_only,
        is_diagnostic_followup=payload.is_diagnostic_followup,
        target_misconception_codes=payload.target_misconception_codes,
        content=payload.content.strip(),
        code_snippet=payload.code_snippet,
        answer_key=payload.answer_key.strip(),
        explanation=payload.explanation.strip(),
        plain_language_explanation=payload.plain_language_explanation,
        worked_example=payload.worked_example,
        hint_ladder=payload.hint_ladder,
        diagram_svg=payload.diagram_svg,
        audio_transcript=payload.audio_transcript,
        version=payload.version,
        status=payload.status,
    )
    db.add(question)
    db.flush()

    for opt in payload.options:
        db.add(
            AnswerOption(
                question_id=question.id,
                option_key=opt.option_key.strip(),
                option_text=opt.option_text.strip(),
                misconception_id=opt.misconception_id,
                secondary_misconception_id=opt.secondary_misconception_id,
                confidence_weight=opt.confidence_weight,
                ambiguity_note=opt.ambiguity_note,
                is_correct=opt.is_correct,
            )
        )

    log_audit_event(
        db,
        action="admin_question_created",
        entity_type="question",
        entity_id=question.stable_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={
            "concept_id": question.concept_id,
            "difficulty": question.difficulty,
            "version": question.version,
        },
    )
    db.commit()
    db.refresh(question)
    return {
        "id": question.id,
        "stable_id": question.stable_id,
        "status": question.status,
        "version": question.version,
    }


@router.put("/questions/{question_id}")
def update_question(
    question_id: int,
    payload: AdminQuestionUpdateRequest,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    if payload.content is not None:
        question.content = payload.content.strip()
    if payload.code_snippet is not None:
        question.code_snippet = payload.code_snippet
    if payload.answer_key is not None:
        question.answer_key = payload.answer_key.strip()
    if payload.explanation is not None:
        question.explanation = payload.explanation.strip()
    if payload.plain_language_explanation is not None:
        question.plain_language_explanation = payload.plain_language_explanation
    if payload.worked_example is not None:
        question.worked_example = payload.worked_example
    if payload.difficulty is not None:
        question.difficulty = payload.difficulty
    if payload.status is not None:
        question.status = payload.status
    if payload.version is not None:
        question.version = payload.version
    if payload.hint_ladder is not None:
        question.hint_ladder = payload.hint_ladder

    log_audit_event(
        db,
        action="admin_question_updated",
        entity_type="question",
        entity_id=question.stable_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={"status": question.status, "version": question.version},
    )
    db.commit()
    return {
        "id": question.id,
        "stable_id": question.stable_id,
        "status": question.status,
        "version": question.version,
    }


@router.post("/questions/{question_id}/archive")
def archive_question(
    question_id: int,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    question.status = "archived"
    log_audit_event(
        db,
        action="admin_question_archived",
        entity_type="question",
        entity_id=question.stable_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={},
    )
    db.commit()
    return {"id": question.id, "stable_id": question.stable_id, "status": question.status}


@router.post("/misconceptions", status_code=status.HTTP_201_CREATED)
def create_misconception(
    payload: AdminMisconceptionCreateRequest,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Misconception)
        .filter(Misconception.code == payload.code)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A misconception rule with this code already exists.",
        )

    misc = Misconception(
        code=payload.code.strip(),
        concept_id=payload.concept_id,
        label=payload.label.strip(),
        description=payload.description.strip(),
        diagnostic_rule=payload.diagnostic_rule.strip(),
        remediation_focus=payload.remediation_focus.strip(),
        rule_version=payload.rule_version.strip(),
        status=payload.status,
    )
    db.add(misc)
    db.flush()

    log_audit_event(
        db,
        action="admin_misconception_rule_created",
        entity_type="misconception",
        entity_id=misc.code,
        actor_id=current_user.id,
        actor_role=current_user.role,
        rule_version=misc.rule_version,
        metadata={"concept_id": misc.concept_id, "label": misc.label},
    )
    db.commit()
    db.refresh(misc)
    return {
        "id": misc.id,
        "code": misc.code,
        "label": misc.label,
        "rule_version": misc.rule_version,
    }


@router.post("/activities", status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: AdminActivityCreateRequest,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Activity)
        .filter(Activity.stable_id == payload.stable_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An activity with this stable_id already exists.",
        )

    act = Activity(
        stable_id=payload.stable_id.strip(),
        concept_id=payload.concept_id,
        target_misconception_id=payload.target_misconception_id,
        title=payload.title.strip(),
        activity_type=payload.activity_type,
        difficulty=payload.difficulty,
        content_ref=payload.content_ref,
        content_body=payload.content_body.strip(),
        plain_language_body=payload.plain_language_body,
        code_example=payload.code_example,
        diagram_svg=payload.diagram_svg,
        audio_transcript=payload.audio_transcript,
        interactive_exercise=payload.interactive_exercise,
        format=payload.format,
        estimated_duration=payload.estimated_duration,
        version=payload.version,
        status=payload.status,
    )
    db.add(act)
    db.flush()

    log_audit_event(
        db,
        action="admin_activity_created",
        entity_type="activity",
        entity_id=act.stable_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={"concept_id": act.concept_id, "format": act.format},
    )
    db.commit()
    db.refresh(act)
    return {"id": act.id, "stable_id": act.stable_id, "title": act.title}


@router.post("/activities/{activity_id}/archive")
def archive_activity(
    activity_id: int,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found.")
    act.status = "archived"
    log_audit_event(
        db,
        action="admin_activity_archived",
        entity_type="activity",
        entity_id=act.stable_id,
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={},
    )
    db.commit()
    return {"id": act.id, "stable_id": act.stable_id, "status": act.status}
