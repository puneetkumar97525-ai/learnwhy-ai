from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Concept, MasteryState


def compute_ema_mastery(
    prior_mastery: float, is_correct: bool, alpha: Optional[float] = None
) -> float:
    """
    Transparent baseline mastery update rule:
        M_new = (1 - alpha) * M_old + alpha * y
    where M_old in [0, 1], y = 1.0 if correct else 0.0, alpha in (0, 1].
    Note: This is a heuristic exponential moving average baseline, not a validated cognitive model.
    """
    rate = alpha if alpha is not None else settings.MASTERY_ALPHA
    rate = max(0.01, min(1.0, float(rate)))
    m_old = max(0.0, min(1.0, float(prior_mastery)))
    y = 1.0 if is_correct else 0.0
    m_new = (1.0 - rate) * m_old + rate * y
    return round(max(0.0, min(1.0, m_new)), 4)


def compute_uncertainty(attempts_count: int) -> float:
    """
    Simple monotonically decreasing uncertainty indicator in [0.10, 0.50]
    based on number of observed attempts on the concept.
    """
    if attempts_count <= 0:
        return 0.50
    return round(max(0.10, 0.50 / (1.0 + 0.35 * attempts_count)), 4)


def mastery_band_label(mastery: float, attempts_count: int) -> str:
    """
    Non-color-only descriptive status label for a concept mastery estimate.
    Never frames mastery as permanent ability.
    """
    if attempts_count == 0:
        return "Not yet practiced (prior estimate)"
    if mastery >= 0.75:
        return "Strong recent evidence"
    if mastery >= 0.50:
        return "Developing understanding"
    return "Needs targeted practice"


def get_or_create_mastery_state(
    db: Session, user_id: int, concept: Concept
) -> MasteryState:
    state = (
        db.query(MasteryState)
        .filter(
            MasteryState.user_id == user_id,
            MasteryState.concept_id == concept.id,
        )
        .first()
    )
    if not state:
        prior = (
            concept.prior_mastery
            if concept.prior_mastery is not None
            else settings.DEFAULT_PRIOR_MASTERY
        )
        state = MasteryState(
            user_id=user_id,
            concept_id=concept.id,
            mastery=round(float(prior), 4),
            attempts_count=0,
            correct_count=0,
            uncertainty=0.50,
            uncertainty_or_evidence=(
                f"Initial prior estimate ({prior:.2f}); 0 attempts recorded."
            ),
            last_alpha=settings.MASTERY_ALPHA,
            model_version=settings.MASTERY_MODEL_VERSION,
        )
        db.add(state)
        db.flush()
    return state


def update_concept_mastery(
    db: Session,
    user_id: int,
    concept: Concept,
    is_correct: bool,
    alpha: Optional[float] = None,
    context_note: str = "practice attempt",
) -> tuple[float, MasteryState]:
    """
    Updates ONLY the concept measured by the question.
    Returns (previous_mastery, updated_state).
    """
    state = get_or_create_mastery_state(db, user_id, concept)
    old_mastery = state.mastery
    used_alpha = alpha if alpha is not None else settings.MASTERY_ALPHA
    new_mastery = compute_ema_mastery(old_mastery, is_correct, alpha=used_alpha)

    state.mastery = new_mastery
    state.attempts_count = (state.attempts_count or 0) + 1
    if is_correct:
        state.correct_count = (state.correct_count or 0) + 1
    state.uncertainty = compute_uncertainty(state.attempts_count)
    state.last_alpha = used_alpha
    state.model_version = settings.MASTERY_MODEL_VERSION
    outcome_word = "correct" if is_correct else "incorrect"
    state.uncertainty_or_evidence = (
        f"Estimated from {state.attempts_count} attempt(s) "
        f"({state.correct_count} correct; uncertainty ±{state.uncertainty:.2f}). "
        f"Last update: {outcome_word} {context_note} "
        f"({old_mastery:.2f} -> {new_mastery:.2f}, alpha={used_alpha:.2f})."
    )
    state.updated_at = datetime.now(timezone.utc)
    db.flush()
    return old_mastery, state
