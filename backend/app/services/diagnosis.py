from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import (
    AnswerOption,
    Attempt,
    Diagnosis,
    Misconception,
    Question,
)


def find_followup_question(
    db: Session,
    concept_id: int,
    exclude_question_id: int,
    candidate_codes: list[str],
) -> Optional[Question]:
    """
    Find a short diagnostic follow-up question for the same concept that helps
    disambiguate between competing misconception hypotheses.
    """
    followups = (
        db.query(Question)
        .filter(
            Question.concept_id == concept_id,
            Question.id != exclude_question_id,
            Question.is_diagnostic_followup == True,  # noqa: E712
            Question.status == "published",
        )
        .all()
    )
    if not followups:
        return None

    if candidate_codes:
        candidate_set = set(candidate_codes)
        for q in followups:
            q_codes = set(q.target_misconception_codes or [])
            if candidate_set.intersection(q_codes):
                return q
    return followups[0]


def diagnose_attempt(
    db: Session,
    attempt: Attempt,
    question: Question,
) -> Diagnosis:
    """
    Transparent rule-based misconception diagnosis engine.
    - Never forces a confident diagnosis from an unmapped or ambiguous error.
    - Distinguishes between:
        1. 'correct_no_error' (correct response)
        2. 'diagnosed' (single clear misconception rule triggered with confidence >= 0.70)
        3. 'ambiguous_followup_needed' (multiple competing misconception causes are plausible,
           or confidence is moderate and a diagnostic follow-up question exists)
        4. 'insufficient_evidence' (wrong answer, but rule mapping is absent or weak with no follow-up)
    """
    normalized_resp = (attempt.response or "").strip()

    if attempt.is_correct:
        diag = Diagnosis(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            concept_id=question.concept_id,
            misconception_id=None,
            candidate_misconceptions=[],
            confidence=1.0,
            evidence=(
                f"Learner answered question {question.stable_id} correctly "
                f"(response='{normalized_resp}'). No misconception indicated."
            ),
            status="correct_no_error",
            followup_question_id=None,
            rule_version=settings.RULE_ENGINE_VERSION,
        )
        db.add(diag)
        db.flush()
        return diag

    # Look up matching answer option (by option_key or option_text)
    matched_option: Optional[AnswerOption] = None
    for opt in question.answer_options:
        if (
            opt.option_key.strip().upper() == normalized_resp.upper()
            or opt.option_text.strip().lower() == normalized_resp.lower()
        ):
            matched_option = opt
            break

    primary_misc: Optional[Misconception] = None
    secondary_misc: Optional[Misconception] = None

    if matched_option and matched_option.misconception_id:
        primary_misc = (
            db.query(Misconception)
            .filter(
                Misconception.id == matched_option.misconception_id,
                Misconception.status == "active",
            )
            .first()
        )
    if matched_option and matched_option.secondary_misconception_id:
        secondary_misc = (
            db.query(Misconception)
            .filter(
                Misconception.id == matched_option.secondary_misconception_id,
                Misconception.status == "active",
            )
            .first()
        )

    # For trace_output or structured_answer without a matched option row, inspect concept misconceptions
    if not primary_misc and not matched_option:
        concept_miscs = (
            db.query(Misconception)
            .filter(
                Misconception.concept_id == question.concept_id,
                Misconception.status == "active",
            )
            .all()
        )
        for m in concept_miscs:
            rule_text = (m.diagnostic_rule or "").strip()
            # Simple pattern rule format: "response_equals:<val>"
            if rule_text.startswith("response_equals:"):
                expected_err = rule_text.split("response_equals:", 1)[1].strip()
                if normalized_resp.lower() == expected_err.lower():
                    primary_misc = m
                    break

    # Case 1: Both primary and secondary misconceptions exist (explicit ambiguity!)
    # or option confidence_weight < 0.70 (low certainty from a single response)
    option_conf = (
        float(matched_option.confidence_weight)
        if matched_option and matched_option.confidence_weight is not None
        else 0.78
    )

    if primary_misc and (secondary_misc is not None or option_conf < 0.70):
        candidates = [
            {
                "id": primary_misc.id,
                "code": primary_misc.code,
                "label": primary_misc.label,
                "probability": round(option_conf, 2),
            }
        ]
        candidate_codes = [primary_misc.code]
        if secondary_misc:
            candidates.append(
                {
                    "id": secondary_misc.id,
                    "code": secondary_misc.code,
                    "label": secondary_misc.label,
                    "probability": round(max(0.25, 1.0 - option_conf), 2),
                }
            )
            candidate_codes.append(secondary_misc.code)

        followup_q = find_followup_question(
            db,
            concept_id=question.concept_id,
            exclude_question_id=question.id,
            candidate_codes=candidate_codes,
        )

        ambiguity_detail = (
            matched_option.ambiguity_note
            if (matched_option and matched_option.ambiguity_note)
            else (
                f"Response '{normalized_resp}' on {question.stable_id} is consistent with multiple "
                f"candidate hypotheses ({', '.join(c['label'] for c in candidates)})."
            )
        )

        if followup_q:
            status_val = "ambiguous_followup_needed"
            evidence_text = (
                f"{ambiguity_detail} A single wrong answer is not sufficient to be certain; "
                f"presenting diagnostic follow-up {followup_q.stable_id} to disambiguate."
            )
        else:
            status_val = "insufficient_evidence"
            evidence_text = (
                f"{ambiguity_detail} Insufficient evidence to confirm a single misconception "
                f"without further observation."
            )

        diag = Diagnosis(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            concept_id=question.concept_id,
            misconception_id=primary_misc.id,
            candidate_misconceptions=candidates,
            confidence=round(min(option_conf, 0.55), 2),
            evidence=evidence_text,
            status=status_val,
            followup_question_id=followup_q.id if followup_q else None,
            rule_version=primary_misc.rule_version or settings.RULE_ENGINE_VERSION,
        )
        db.add(diag)
        db.flush()
        return diag

    # Case 2: Clear single misconception mapped with confidence >= 0.70
    if primary_misc:
        candidates = [
            {
                "id": primary_misc.id,
                "code": primary_misc.code,
                "label": primary_misc.label,
                "probability": round(option_conf, 2),
            }
        ]
        diag = Diagnosis(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            concept_id=question.concept_id,
            misconception_id=primary_misc.id,
            candidate_misconceptions=candidates,
            confidence=round(option_conf, 2),
            evidence=(
                f"Selected distractor '{normalized_resp}' on {question.stable_id} matches rule "
                f"[{primary_misc.code}]: {primary_misc.diagnostic_rule}. "
                f"Treated as a candidate misconception (confidence {option_conf:.2f}), not a permanent trait."
            ),
            status="diagnosed",
            followup_question_id=None,
            rule_version=primary_misc.rule_version or settings.RULE_ENGINE_VERSION,
        )
        db.add(diag)
        db.flush()
        return diag

    # Case 3: Unmapped wrong response -> insufficient evidence
    diag = Diagnosis(
        attempt_id=attempt.id,
        user_id=attempt.user_id,
        concept_id=question.concept_id,
        misconception_id=None,
        candidate_misconceptions=[],
        confidence=0.20,
        evidence=(
            f"Response '{normalized_resp}' on {question.stable_id} is incorrect, "
            f"but insufficient evidence exists from this single answer to assign a specific misconception label."
        ),
        status="insufficient_evidence",
        followup_question_id=None,
        rule_version=settings.RULE_ENGINE_VERSION,
    )
    db.add(diag)
    db.flush()
    return diag


def resolve_diagnostic_followup(
    db: Session,
    diagnosis: Diagnosis,
    followup_question: Question,
    followup_attempt: Attempt,
) -> Diagnosis:
    """
    Updates an ambiguous diagnosis based on the learner's response to the
    short diagnostic follow-up question.
    """
    normalized_resp = (followup_attempt.response or "").strip()
    diagnosis.followup_attempt_id = followup_attempt.id

    if followup_attempt.is_correct:
        # Correct follow-up reduces confidence in a deep misconception (likely an execution slip)
        diagnosis.status = "insufficient_evidence"
        diagnosis.confidence = 0.30
        diagnosis.evidence = (
            f"{diagnosis.evidence} | Follow-up {followup_question.stable_id} was answered correctly "
            f"('{normalized_resp}'), suggesting the earlier error may have been a momentary slip rather "
            f"than a persistent misconception."
        )
        db.flush()
        return diagnosis

    # Incorrect follow-up: check which misconception distractor was chosen on the follow-up
    matched_option = None
    for opt in followup_question.answer_options:
        if (
            opt.option_key.strip().upper() == normalized_resp.upper()
            or opt.option_text.strip().lower() == normalized_resp.lower()
        ):
            matched_option = opt
            break

    if matched_option and matched_option.misconception_id:
        confirmed = (
            db.query(Misconception)
            .filter(Misconception.id == matched_option.misconception_id)
            .first()
        )
        if confirmed:
            diagnosis.misconception_id = confirmed.id
            diagnosis.status = "resolved_by_followup"
            diagnosis.confidence = 0.88
            diagnosis.candidate_misconceptions = [
                {
                    "id": confirmed.id,
                    "code": confirmed.code,
                    "label": confirmed.label,
                    "probability": 0.88,
                }
            ]
            diagnosis.evidence = (
                f"{diagnosis.evidence} | Follow-up {followup_question.stable_id} response '{normalized_resp}' "
                f"confirmed candidate misconception [{confirmed.code}: {confirmed.label}] "
                f"(updated confidence 0.88)."
            )
            db.flush()
            return diagnosis

    # If follow-up was wrong but didn't match a specific distractor, keep primary candidate at moderate confidence
    diagnosis.status = "insufficient_evidence"
    diagnosis.confidence = 0.45
    diagnosis.evidence = (
        f"{diagnosis.evidence} | Follow-up {followup_question.stable_id} response '{normalized_resp}' "
        f"remained inconclusive; recommending general concept review."
    )
    db.flush()
    return diagnosis
