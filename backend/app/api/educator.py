import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.entities import (
    Attempt,
    Concept,
    Diagnosis,
    InterventionOutcome,
    MasteryState,
    Misconception,
    Question,
    User,
)
from app.schemas.api_schemas import EducatorNoteRequest
from app.services.audit import log_audit_event

router = APIRouter(prefix="/api/educator", tags=["educator"])


@router.get("/classes/{class_id}/analytics")
def get_class_analytics(
    class_id: int,
    concept_id: Optional[int] = Query(default=None),
    current_user: User = Depends(require_roles(["educator", "admin"])),
    db: Session = Depends(get_db),
):
    students = (
        db.query(User)
        .filter(User.role == "student", User.status == "active")
        .all()
    )
    student_map = {s.id: s for s in students}
    concepts = (
        db.query(Concept)
        .filter(Concept.status == "published")
        .order_by(Concept.order_index.asc())
        .all()
    )
    if concept_id is not None:
        concepts_filtered = [c for c in concepts if c.id == concept_id]
    else:
        concepts_filtered = concepts

    concept_map = {c.id: c for c in concepts}
    questions = db.query(Question).all()
    q_to_concept = {q.id: q.concept_id for q in questions}
    misc_map = {m.id: m for m in db.query(Misconception).all()}

    all_attempts = db.query(Attempt).all()
    all_mastery = db.query(MasteryState).all()
    all_diagnoses = db.query(Diagnosis).all()
    all_outcomes = (
        db.query(InterventionOutcome)
        .order_by(InterventionOutcome.created_at.desc())
        .all()
    )

    # Concept-level performance
    concept_performance = []
    for c in concepts_filtered:
        c_mastery_rows = [
            m for m in all_mastery if m.concept_id == c.id and m.user_id in student_map
        ]
        avg_m = (
            sum(m.mastery for m in c_mastery_rows) / len(c_mastery_rows)
            if c_mastery_rows
            else c.prior_mastery
        )
        c_attempts = [
            a for a in all_attempts if q_to_concept.get(a.question_id) == c.id
        ]
        c_correct = sum(1 for a in c_attempts if a.is_correct)
        acc_pct = (
            round((c_correct / len(c_attempts)) * 100, 1)
            if c_attempts
            else 0.0
        )
        below_thresh = sum(
            1 for m in c_mastery_rows if m.mastery < 0.45 and m.attempts_count >= 1
        )
        concept_performance.append(
            {
                "concept_id": c.id,
                "slug": c.slug,
                "concept_name": c.name,
                "order_index": c.order_index,
                "average_mastery": round(avg_m, 3),
                "average_mastery_percent": int(round(avg_m * 100)),
                "total_attempts": len(c_attempts),
                "accuracy_percent": acc_pct,
                "students_needing_review": below_thresh,
            }
        )

    # Common misconceptions aggregation
    misc_counts: dict[int, list[Diagnosis]] = {}
    for d in all_diagnoses:
        if concept_id is not None and d.concept_id != concept_id:
            continue
        if d.misconception_id and d.status in (
            "diagnosed",
            "resolved_by_followup",
            "ambiguous_followup_needed",
        ):
            misc_counts.setdefault(d.misconception_id, []).append(d)

    common_misconceptions = []
    for mid, d_list in misc_counts.items():
        m_obj = misc_map.get(mid)
        if not m_obj:
            continue
        c_obj = concept_map.get(m_obj.concept_id)
        avg_conf = sum(d.confidence for d in d_list) / len(d_list)
        common_misconceptions.append(
            {
                "misconception_id": m_obj.id,
                "code": m_obj.code,
                "label": m_obj.label,
                "concept_id": m_obj.concept_id,
                "concept_name": c_obj.name if c_obj else "Python",
                "occurrences": len(d_list),
                "average_confidence": round(avg_conf, 2),
                "rule_version": m_obj.rule_version,
                "remediation_focus": m_obj.remediation_focus,
            }
        )
    common_misconceptions.sort(key=lambda x: (-x["occurrences"], x["code"]))

    # Learners flagged for supportive review (transparent alert criteria)
    learners_for_review = []
    for m in all_mastery:
        if concept_id is not None and m.concept_id != concept_id:
            continue
        student = student_map.get(m.user_id)
        concept = concept_map.get(m.concept_id)
        if not student or not concept:
            continue

        user_diags = [
            d
            for d in all_diagnoses
            if d.user_id == student.id
            and d.concept_id == concept.id
            and d.misconception_id is not None
        ]
        recurring_misc_label = None
        if len(user_diags) >= 1:
            last_m = misc_map.get(user_diags[-1].misconception_id)
            if last_m:
                recurring_misc_label = last_m.label

        if (m.attempts_count >= 2 and m.mastery < 0.48) or len(user_diags) >= 2:
            criteria_reason = []
            if m.attempts_count >= 2 and m.mastery < 0.48:
                criteria_reason.append(
                    f"Concept mastery estimate is {int(round(m.mastery * 100))}% (< 48% threshold) across {m.attempts_count} attempts"
                )
            if len(user_diags) >= 2:
                criteria_reason.append(
                    f"{len(user_diags)} misconception-flagged attempts recorded on {concept.name}"
                )
            learners_for_review.append(
                {
                    "user_id": student.id,
                    "student_name": student.full_name,
                    "concept_id": concept.id,
                    "concept_name": concept.name,
                    "mastery_estimate": round(m.mastery, 3),
                    "mastery_percent": int(round(m.mastery * 100)),
                    "attempts_count": m.attempts_count,
                    "candidate_misconception": recurring_misc_label or "Unmapped / general review",
                    "alert_reason": "; ".join(criteria_reason),
                    "alert_rule": "Rule: (attempts >= 2 AND mastery < 0.48) OR (concept_misconception_flags >= 2)",
                }
            )

    # Intervention outcomes
    filtered_outcomes = [
        o
        for o in all_outcomes
        if (concept_id is None or o.concept_id == concept_id)
    ]
    verif_correct = sum(
        1 for o in filtered_outcomes if o.immediate_outcome == "improved"
    )
    recurred_count = sum(1 for o in filtered_outcomes if o.error_recurred)

    verif_acc = (
        round((verif_correct / len(filtered_outcomes)) * 100, 1)
        if filtered_outcomes
        else 0.0
    )
    recurrence_rate = (
        round((recurred_count / len(filtered_outcomes)) * 100, 1)
        if filtered_outcomes
        else 0.0
    )
    overall_acc = (
        round(
            (sum(1 for a in all_attempts if a.is_correct) / len(all_attempts)) * 100,
            1,
        )
        if all_attempts
        else 0.0
    )

    return {
        "class_id": class_id,
        "class_name": "MCA Python Foundations Cohort (Demo Sample Data)",
        "alert_methodology_note": (
            "Supportive review flags are generated deterministically when a learner's concept mastery "
            "estimate remains below 48% after at least 2 attempts, or when 2+ attempts trigger a candidate "
            "misconception rule. Educators can inspect the evidence and add review notes."
        ),
        "summary": {
            "active_students": len(students),
            "total_attempts": len(all_attempts),
            "overall_accuracy_percent": overall_acc,
            "total_interventions_verified": len(filtered_outcomes),
            "immediate_verification_accuracy_percent": verif_acc,
            "error_recurrence_rate_percent": recurrence_rate,
        },
        "concept_performance": concept_performance,
        "common_misconceptions": common_misconceptions,
        "learners_flagged_for_review": learners_for_review,
        "intervention_outcomes": [
            {
                "id": o.id,
                "recommendation_id": o.recommendation_id,
                "student_name": (
                    student_map[o.user_id].full_name
                    if o.user_id in student_map
                    else f"Learner #{o.user_id}"
                ),
                "concept_name": (
                    concept_map[o.concept_id].name
                    if o.concept_id in concept_map
                    else "Python"
                ),
                "pre_mastery": round(o.pre_mastery, 3),
                "post_mastery": round(o.post_mastery, 3),
                "immediate_outcome": o.immediate_outcome,
                "error_recurred": o.error_recurred,
                "original_misconception": (
                    misc_map[o.original_misconception_id].label
                    if o.original_misconception_id and o.original_misconception_id in misc_map
                    else None
                ),
                "completion_seconds": o.completion_seconds,
                "educator_note": o.educator_note,
                "educator_acknowledged": o.educator_Acknowledged,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in filtered_outcomes[:20]
        ],
    }


@router.post("/classes/{class_id}/acknowledge")
def acknowledge_outcome_alert(
    class_id: int,
    payload: EducatorNoteRequest,
    current_user: User = Depends(require_roles(["educator", "admin"])),
    db: Session = Depends(get_db),
):
    outcome = (
        db.query(InterventionOutcome)
        .filter(InterventionOutcome.id == payload.outcome_id)
        .first()
    )
    if not outcome:
        raise HTTPException(status_code=404, detail="Intervention outcome not found.")

    outcome.educator_note = payload.educator_note.strip()
    outcome.educator_Acknowledged = payload.acknowledged

    log_audit_event(
        db,
        action="educator_note_recorded",
        entity_type="intervention_outcome",
        entity_id=str(outcome.id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={"class_id": class_id, "acknowledged": payload.acknowledged},
    )
    db.commit()
    return {
        "outcome_id": outcome.id,
        "educator_note": outcome.educator_note,
        "educator_acknowledged": outcome.educator_Acknowledged,
    }


@router.get("/classes/{class_id}/export")
def export_class_analytics_csv(
    class_id: int,
    current_user: User = Depends(require_roles(["educator", "admin"])),
    db: Session = Depends(get_db),
):
    analytics = get_class_analytics(
        class_id=class_id, concept_id=None, current_user=current_user, db=db
    )
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Report Section",
            "Concept / Misconception",
            "Metric 1 (Avg Mastery / Occurrences)",
            "Metric 2 (Attempts / Confidence)",
            "Metric 3 (Accuracy % / Rule Version)",
            "Learners Flagged for Review",
        ]
    )
    for cp in analytics["concept_performance"]:
        writer.writerow(
            [
                "Concept Performance",
                cp["concept_name"],
                f"{cp['average_mastery_percent']}%",
                cp["total_attempts"],
                f"{cp['accuracy_percent']}%",
                cp["students_needing_review"],
            ]
        )
    for cm in analytics["common_misconceptions"]:
        writer.writerow(
            [
                "Recurring Misconception",
                f"{cm['code']} - {cm['label']} ({cm['concept_name']})",
                cm["occurrences"],
                cm["average_confidence"],
                cm["rule_version"],
                "-",
            ]
        )
    for io_row in analytics["intervention_outcomes"]:
        writer.writerow(
            [
                "Intervention Outcome (Aggregate)",
                io_row["concept_name"],
                f"{io_row['pre_mastery']} -> {io_row['post_mastery']}",
                io_row["immediate_outcome"],
                f"Error recurred: {io_row['error_recurred']}",
                "-",
            ]
        )

    log_audit_event(
        db,
        action="educator_csv_exported",
        entity_type="class",
        entity_id=str(class_id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={"class_id": class_id},
    )
    db.commit()

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=learnwhy_class_{class_id}_aggregate_report.csv"
        },
    )
