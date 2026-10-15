from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import (
    Activity,
    Attempt,
    Concept,
    ConceptPrerequisite,
    Diagnosis,
    LearnerPreference,
    MasteryState,
    Misconception,
    Question,
    Recommendation,
)


def compute_prerequisite_maps(
    db: Session, course_id: Optional[int] = None
) -> tuple[dict[int, list[int]], dict[int, list[int]]]:
    """
    Returns:
      - prereqs_of[concept_id]: list of prerequisite concept_ids required before concept_id
      - dependents_of[concept_id]: list of downstream concept_ids that depend on concept_id
    """
    edges = db.query(ConceptPrerequisite).all()
    prereqs_of: dict[int, list[int]] = {}
    dependents_of: dict[int, list[int]] = {}
    for edge in edges:
        prereqs_of.setdefault(edge.concept_id, []).append(edge.prerequisite_id)
        dependents_of.setdefault(edge.prerequisite_id, []).append(edge.concept_id)
    return prereqs_of, dependents_of


def count_all_downstream(concept_id: int, dependents_of: dict[int, list[int]]) -> int:
    visited = set()
    stack = list(dependents_of.get(concept_id, []))
    while stack:
        curr = stack.pop()
        if curr not in visited:
            visited.add(curr)
            stack.extend(dependents_of.get(curr, []))
    return len(visited)


def score_activity_proposed(
    activity: Activity,
    concept: Concept,
    mastery: float,
    attempts_count: int,
    has_demonstrated_error_in_concept: bool,
    prereq_masteries_and_attempts: list[tuple[float, int]],
    downstream_count: int,
    max_downstream: int,
    active_misconception_ids: set[int],
    preferred_formats: list[str],
    recently_completed_activity_ids: set[int],
    w_gap: Optional[float] = None,
    w_prereq: Optional[float] = None,
    w_diff: Optional[float] = None,
) -> tuple[float, dict, str]:
    """
    Proposed explainable recommendation formula (PRD Section 7.4):
        R(activity) = w_gap * gap_relevance + w_prereq * prerequisite_importance + w_diff * difficulty_fit
    Default provisional weights: 0.50, 0.30, 0.20.
    Each component is normalized to [0, 1].
    """
    wg = w_gap if w_gap is not None else settings.REC_WEIGHT_GAP
    wp = w_prereq if w_prereq is not None else settings.REC_WEIGHT_PREREQ
    wd = w_diff if w_diff is not None else settings.REC_WEIGHT_DIFFICULTY

    # 1. Gap relevance G(a) in [0, 1]: how directly the activity addresses a demonstrated gap
    base_deficit = max(0.0, min(1.0, 1.0 - mastery))
    targets_active_misconception = (
        activity.target_misconception_id is not None
        and activity.target_misconception_id in active_misconception_ids
    )
    if targets_active_misconception:
        gap_relevance = min(1.0, 0.65 * base_deficit + 0.45)
    elif has_demonstrated_error_in_concept:
        gap_relevance = min(0.92, 0.70 * base_deficit + 0.30)
    elif mastery >= 0.80 and attempts_count > 0:
        gap_relevance = max(0.05, base_deficit * 0.35)
    elif attempts_count == 0:
        # Untested prior: lower than a demonstrated gap from an actual attempt
        gap_relevance = round(0.55 * base_deficit, 4)
    else:
        gap_relevance = base_deficit
    gap_relevance = round(max(0.0, min(1.0, gap_relevance)), 4)

    # 2. Prerequisite importance P(a) in [0, 1]
    norm_downstream = (
        (downstream_count / max_downstream) if max_downstream > 0 else 0.5
    )
    # A prerequisite blocks readiness only if the learner has attempted it and scored below 0.35
    unmet_prereqs = [
        m for (m, att_cnt) in prereq_masteries_and_attempts if att_cnt > 0 and m < 0.35
    ]
    prereq_readiness = 1.0 if not unmet_prereqs else 0.45
    prerequisite_importance = round(
        max(0.0, min(1.0, (0.45 + 0.55 * norm_downstream) * prereq_readiness)), 4
    )

    # 3. Difficulty & preference fit D(a) in [0, 1]
    if mastery <= 0.45 or attempts_count == 0:
        ideal_difficulty = 1
    elif mastery < 0.72:
        ideal_difficulty = 2
    else:
        ideal_difficulty = 3

    diff_distance = abs((activity.difficulty or 1) - ideal_difficulty)
    base_diff_fit = max(0.20, 1.0 - 0.35 * diff_distance)

    format_bonus = (
        0.08
        if (activity.format in preferred_formats or activity.format == "multimodal")
        else 0.0
    )
    repeat_penalty = 0.35 if activity.id in recently_completed_activity_ids else 0.0
    difficulty_fit = round(
        max(0.0, min(1.0, base_diff_fit + format_bonus - repeat_penalty)), 4
    )

    total_score = round(
        wg * gap_relevance + wp * prerequisite_importance + wd * difficulty_fit, 4
    )

    components = {
        "gap_relevance": gap_relevance,
        "prerequisite_importance": prerequisite_importance,
        "difficulty_fit": difficulty_fit,
        "weights": {
            "gap_relevance": wg,
            "prerequisite_importance": wp,
            "difficulty_fit": wd,
        },
        "formula": "R = 0.50*gap_relevance + 0.30*prerequisite_importance + 0.20*difficulty_fit",
        "concept_mastery_estimate": round(mastery, 3),
        "targets_diagnosed_misconception": targets_active_misconception,
        "demonstrated_concept_gap": has_demonstrated_error_in_concept,
        "prerequisites_ready": len(unmet_prereqs) == 0,
        "recently_completed_penalty_applied": activity.id in recently_completed_activity_ids,
    }

    reason_parts = []
    if targets_active_misconception:
        reason_parts.append(
            f"Recommended because your recent answers suggest a specific concept gap in {concept.name} "
            f"(estimated mastery {int(round(mastery * 100))}%) that this activity directly addresses"
        )
    elif has_demonstrated_error_in_concept:
        reason_parts.append(
            f"Recommended because your recent attempt in {concept.name} showed an error "
            f"(current mastery estimate {int(round(mastery * 100))}%) and targeted review can help consolidate the concept"
        )
    else:
        reason_parts.append(
            f"Recommended because {concept.name} currently has an estimated mastery of {int(round(mastery * 100))}%"
        )

    if downstream_count > 0 and len(unmet_prereqs) == 0:
        reason_parts.append(
            f"it serves as a foundation for {downstream_count} subsequent Python concept(s)"
        )
    elif len(unmet_prereqs) > 0:
        reason_parts.append(
            "Note: strengthening earlier prerequisite concepts first may make this topic easier"
        )

    reason_parts.append(
        f"and its difficulty (Level {activity.difficulty}) matches your current progress."
    )
    reason = ", ".join(reason_parts)

    return total_score, components, reason


def score_activity_baseline(
    activity: Activity,
    concept: Concept,
    mastery: float,
    recently_completed_activity_ids: set[int],
) -> tuple[float, dict, str]:
    """
    Simpler score-based baseline for research evaluation comparison (Baseline A):
    Ranks activities solely by raw concept mastery deficit (1 - M_c) and difficulty level,
    ignoring misconception diagnosis, demonstrated attempt evidence, and prerequisite graph structure.
    """
    gap_score = round(max(0.0, min(1.0, 1.0 - mastery)), 4)
    diff_score = round(1.0 / float(max(1, activity.difficulty or 1)), 4)
    repeat_penalty = 0.25 if activity.id in recently_completed_activity_ids else 0.0
    total_score = round(max(0.0, 0.80 * gap_score + 0.20 * diff_score - repeat_penalty), 4)
    components = {
        "gap_relevance": gap_score,
        "prerequisite_importance": 0.0,
        "difficulty_fit": diff_score,
        "weights": {"gap_relevance": 0.80, "prerequisite_importance": 0.0, "difficulty_fit": 0.20},
        "formula": "Baseline_A = 0.80*(1 - mastery) + 0.20*(1/difficulty)",
        "concept_mastery_estimate": round(mastery, 3),
        "targets_diagnosed_misconception": False,
    }
    reason = (
        f"Baseline score recommendation: selected {concept.name} based on overall concept score "
        f"({int(round(mastery * 100))}%) without misconception disambiguation."
    )
    return total_score, components, reason


def generate_recommendations_for_user(
    db: Session,
    user_id: int,
    strategy: str = "proposed",
    limit: int = 5,
    trigger_attempt_id: Optional[int] = None,
    trigger_diagnosis_id: Optional[int] = None,
) -> list[Recommendation]:
    """
    Computes ranked recommendations for a student, persists the top recommendations
    with full score components and human-readable reasons, and returns them.
    """
    activities = (
        db.query(Activity).filter(Activity.status == "published").all()
    )
    if not activities:
        return []

    concepts = {c.id: c for c in db.query(Concept).all()}
    mastery_rows = (
        db.query(MasteryState).filter(MasteryState.user_id == user_id).all()
    )
    mastery_map = {m.concept_id: m.mastery for m in mastery_rows}
    attempts_cnt_map = {m.concept_id: (m.attempts_count or 0) for m in mastery_rows}

    # Find concepts where learner has recent incorrect attempts (demonstrated gap)
    recent_wrong_attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == user_id, Attempt.is_correct == False)  # noqa: E712
        .order_by(Attempt.submitted_at.desc())
        .limit(8)
        .all()
    )
    q_ids = {a.question_id for a in recent_wrong_attempts}
    demonstrated_gap_concept_ids = set()
    if q_ids:
        for q in db.query(Question).filter(Question.id.in_(q_ids)).all():
            demonstrated_gap_concept_ids.add(q.concept_id)

    prefs = (
        db.query(LearnerPreference)
        .filter(LearnerPreference.user_id == user_id)
        .first()
    )
    preferred_formats = (
        prefs.preferred_formats
        if (prefs and isinstance(prefs.preferred_formats, list))
        else ["text", "diagram", "interactive"]
    )

    # Identify active/recent diagnosed misconceptions for this learner
    recent_diags = (
        db.query(Diagnosis)
        .filter(
            Diagnosis.user_id == user_id,
            Diagnosis.status.in_(["diagnosed", "resolved_by_followup", "ambiguous_followup_needed"]),
            Diagnosis.misconception_id.isnot(None),
        )
        .order_by(Diagnosis.created_at.desc())
        .limit(10)
        .all()
    )
    active_misconception_ids = {
        d.misconception_id for d in recent_diags if d.misconception_id is not None
    }
    misconception_lookup = {
        m.id: m for m in db.query(Misconception).filter(Misconception.id.in_(active_misconception_ids)).all()
    } if active_misconception_ids else {}

    completed_recs = (
        db.query(Recommendation)
        .filter(
            Recommendation.user_id == user_id,
            Recommendation.status.in_(["completed", "verified"]),
        )
        .order_by(Recommendation.created_at.desc())
        .limit(6)
        .all()
    )
    recently_completed_activity_ids = {r.activity_id for r in completed_recs}

    prereqs_of, dependents_of = compute_prerequisite_maps(db)
    downstream_counts = {
        cid: count_all_downstream(cid, dependents_of) for cid in concepts
    }
    max_downstream = max(downstream_counts.values(), default=1) or 1

    scored_items = []
    for act in activities:
        concept = concepts.get(act.concept_id)
        if not concept or concept.status != "published":
            continue
        m_val = mastery_map.get(
            concept.id,
            concept.prior_mastery if concept.prior_mastery is not None else settings.DEFAULT_PRIOR_MASTERY,
        )
        att_cnt = attempts_cnt_map.get(concept.id, 0)
        prereq_ids = prereqs_of.get(concept.id, [])
        prereq_info = [
            (
                mastery_map.get(pid, settings.DEFAULT_PRIOR_MASTERY),
                attempts_cnt_map.get(pid, 0),
            )
            for pid in prereq_ids
        ]

        if strategy == "baseline_score":
            total, comps, reason = score_activity_baseline(
                activity=act,
                concept=concept,
                mastery=m_val,
                recently_completed_activity_ids=recently_completed_activity_ids,
            )
        else:
            total, comps, reason = score_activity_proposed(
                activity=act,
                concept=concept,
                mastery=m_val,
                attempts_count=att_cnt,
                has_demonstrated_error_in_concept=(concept.id in demonstrated_gap_concept_ids),
                prereq_masteries_and_attempts=prereq_info,
                downstream_count=downstream_counts.get(concept.id, 0),
                max_downstream=max_downstream,
                active_misconception_ids=active_misconception_ids,
                preferred_formats=preferred_formats,
                recently_completed_activity_ids=recently_completed_activity_ids,
            )
            if (
                act.target_misconception_id
                and act.target_misconception_id in misconception_lookup
            ):
                misc_obj = misconception_lookup[act.target_misconception_id]
                comps["targeted_misconception_code"] = misc_obj.code
                comps["targeted_misconception_label"] = misc_obj.label
                reason = (
                    f"Recommended because your recent responses indicate a possible misconception on "
                    f"'{misc_obj.label}' in {concept.name} (estimated mastery {int(round(m_val * 100))}%). "
                    f"This {act.activity_type.replace('_', ' ')} directly targets that concept gap."
                )

        scored_items.append((total, act, concept, comps, reason))

    scored_items.sort(
        key=lambda item: (-item[0], item[2].order_index, item[1].id)
    )
    selected = scored_items[:limit]

    db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.strategy == strategy,
        Recommendation.status == "pending",
    ).update({"status": "dismissed"}, synchronize_session=False)

    created_recs: list[Recommendation] = []
    for idx, (score_val, act, concept, comps, reason) in enumerate(selected, start=1):
        rec = Recommendation(
            user_id=user_id,
            activity_id=act.id,
            concept_id=concept.id,
            trigger_attempt_id=trigger_attempt_id,
            trigger_diagnosis_id=trigger_diagnosis_id,
            strategy=strategy,
            total_score=score_val,
            score_components=comps,
            reason=reason,
            rank=idx,
            status="pending",
            rule_version=settings.RULE_ENGINE_VERSION,
        )
        db.add(rec)
        created_recs.append(rec)

    db.flush()
    return created_recs
