from sqlalchemy.orm import Session

from app.models.entities import (
    Achievement,
    Attempt,
    InterventionOutcome,
    MasteryState,
    User,
    UserAchievement,
)


def award_points_and_check_achievements(
    db: Session,
    user: User,
    event_type: str,
    is_correct: bool = False,
) -> list[dict]:
    """
    Supportive, non-punitive gamification engine (SRC-3):
    - Awards points for effort and learning milestones.
    - Never penalizes learners for using hints, accessibility preferences, or taking extra time.
    - Never locks core learning content behind points or streaks.
    """
    points_delta = 0
    if event_type == "attempt":
        # Effort is always rewarded; correct answer adds a bonus
        points_delta = 15 if is_correct else 5
    elif event_type == "diagnostic_followup":
        points_delta = 10
    elif event_type == "intervention_complete":
        points_delta = 20
    elif event_type == "verification_complete":
        points_delta = 25 if is_correct else 10

    user.points = (user.points or 0) + points_delta
    if user.streak_opt_in and (user.current_streak or 0) == 0:
        user.current_streak = 1

    # Check achievements
    all_achievements = db.query(Achievement).all()
    earned_ids = {
        ua.achievement_id
        for ua in db.query(UserAchievement)
        .filter(UserAchievement.user_id == user.id)
        .all()
    }

    attempts_count = (
        db.query(Attempt).filter(Attempt.user_id == user.id).count()
    )
    verified_count = (
        db.query(InterventionOutcome)
        .filter(InterventionOutcome.user_id == user.id)
        .count()
    )
    strong_concepts = (
        db.query(MasteryState)
        .filter(
            MasteryState.user_id == user.id,
            MasteryState.mastery >= 0.70,
        )
        .count()
    )

    newly_earned: list[dict] = []
    for ach in all_achievements:
        if ach.id in earned_ids:
            continue
        criteria = ach.criteria or {}
        ctype = criteria.get("type")
        threshold = int(criteria.get("threshold", 1))

        qualifies = False
        if ctype == "attempts_count" and attempts_count >= threshold:
            qualifies = True
        elif ctype == "verified_interventions" and verified_count >= threshold:
            qualifies = True
        elif ctype == "strong_concepts" and strong_concepts >= threshold:
            qualifies = True
        elif ctype == "points_total" and (user.points or 0) >= threshold:
            qualifies = True

        if qualifies:
            ua = UserAchievement(user_id=user.id, achievement_id=ach.id)
            db.add(ua)
            user.points = (user.points or 0) + (ach.points_reward or 0)
            newly_earned.append(
                {
                    "code": ach.code,
                    "name": ach.name,
                    "description": ach.description,
                    "points_reward": ach.points_reward,
                }
            )

    db.flush()
    return newly_earned
