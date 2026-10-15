from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    rate_limit_auth,
    verify_password,
)
from app.models.entities import (
    Attempt,
    Course,
    Diagnosis,
    InterventionOutcome,
    LearnerPreference,
    MasteryState,
    User,
)
from app.schemas.api_schemas import (
    LoginRequest,
    PreferenceUpdateRequest,
    RegisterRequest,
)
from app.services.audit import log_audit_event
from app.services.mastery import get_or_create_mastery_state

router = APIRouter(prefix="/api/auth", tags=["auth"])


def serialize_user(db: Session, user: User) -> dict:
    prefs = (
        db.query(LearnerPreference)
        .filter(LearnerPreference.user_id == user.id)
        .first()
    )
    if not prefs:
        prefs = LearnerPreference(
            user_id=user.id,
            language="en",
            text_size="normal",
            reduced_motion=False,
            high_contrast=False,
            plain_language_mode=False,
            preferred_formats=["text", "diagram", "interactive", "audio"],
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "status": user.status,
        "onboarding_completed": user.onboarding_completed,
        "selected_course_id": user.selected_course_id,
        "points": user.points,
        "current_streak": user.current_streak,
        "daily_goal_minutes": user.daily_goal_minutes,
        "streak_opt_in": user.streak_opt_in,
        "preferences": {
            "language": prefs.language,
            "text_size": prefs.text_size,
            "reduced_motion": prefs.reduced_motion,
            "high_contrast": prefs.high_contrast,
            "plain_language_mode": prefs.plain_language_mode,
            "preferred_formats": prefs.preferred_formats or ["text", "diagram", "interactive"],
        },
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    _rl: None = Depends(rate_limit_auth),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    default_course = (
        db.query(Course).filter(Course.status == "published").first()
    )
    user = User(
        email=payload.email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        status="active",
        onboarding_completed=False,
        selected_course_id=default_course.id if default_course else None,
        points=0,
        current_streak=1,
        daily_goal_minutes=20,
        streak_opt_in=True,
    )
    db.add(user)
    db.flush()

    prefs = LearnerPreference(
        user_id=user.id,
        language="en",
        text_size="normal",
        reduced_motion=False,
        high_contrast=False,
        plain_language_mode=False,
        preferred_formats=["text", "diagram", "interactive", "audio"],
    )
    db.add(prefs)

    if default_course and user.role == "student":
        for concept in default_course.concepts:
            get_or_create_mastery_state(db, user.id, concept)

    log_audit_event(
        db,
        action="user_registered",
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        actor_role=user.role,
        metadata={"role": user.role},
    )
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(db, user),
    }


@router.post("/login")
def login(
    payload: LoginRequest,
    _rl: None = Depends(rate_limit_auth),
    db: Session = Depends(get_db),
):
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active.",
        )

    log_audit_event(
        db,
        action="user_login",
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        actor_role=user.role,
        metadata={},
    )
    db.commit()

    token = create_access_token(subject=str(user.id), role=user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(db, user),
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"user": serialize_user(db, current_user)}


@router.put("/preferences")
def update_preferences(
    payload: PreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = (
        db.query(LearnerPreference)
        .filter(LearnerPreference.user_id == current_user.id)
        .first()
    )
    if not prefs:
        prefs = LearnerPreference(user_id=current_user.id)
        db.add(prefs)

    prefs.language = payload.language
    prefs.text_size = payload.text_size
    prefs.reduced_motion = payload.reduced_motion
    prefs.high_contrast = payload.high_contrast
    prefs.plain_language_mode = payload.plain_language_mode
    prefs.preferred_formats = payload.preferred_formats

    if payload.selected_course_id is not None:
        current_user.selected_course_id = payload.selected_course_id
    current_user.daily_goal_minutes = payload.daily_goal_minutes
    current_user.streak_opt_in = payload.streak_opt_in
    current_user.onboarding_completed = payload.onboarding_completed

    log_audit_event(
        db,
        action="preferences_updated",
        entity_type="learner_preferences",
        entity_id=str(current_user.id),
        actor_id=current_user.id,
        actor_role=current_user.role,
        metadata={
            "language": prefs.language,
            "text_size": prefs.text_size,
            "reduced_motion": prefs.reduced_motion,
            "plain_language_mode": prefs.plain_language_mode,
            "preferred_formats": prefs.preferred_formats,
        },
    )
    db.commit()
    db.refresh(current_user)
    return {"user": serialize_user(db, current_user)}


@router.get("/export-my-data")
def export_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Privacy & transparency endpoint (FR-22): allows an authenticated learner
    to inspect and export all learning records stored for their account.
    """
    mastery = (
        db.query(MasteryState)
        .filter(MasteryState.user_id == current_user.id)
        .all()
    )
    attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.submitted_at.desc())
        .all()
    )
    diagnoses = (
        db.query(Diagnosis)
        .filter(Diagnosis.user_id == current_user.id)
        .order_by(Diagnosis.created_at.desc())
        .all()
    )
    outcomes = (
        db.query(InterventionOutcome)
        .filter(InterventionOutcome.user_id == current_user.id)
        .all()
    )
    return {
        "user": serialize_user(db, current_user),
        "privacy_notice": (
            "LearnWhy AI stores concept mastery estimates, question attempts, and candidate misconception "
            "diagnoses solely to personalize your learning path. Estimates are heuristic indicators of recent "
            "practice, not definitive measures of ability."
        ),
        "mastery_states": [
            {
                "concept_id": m.concept_id,
                "mastery": m.mastery,
                "attempts_count": m.attempts_count,
                "uncertainty": m.uncertainty,
                "evidence": m.uncertainty_or_evidence,
                "model_version": m.model_version,
            }
            for m in mastery
        ],
        "attempts_count": len(attempts),
        "diagnoses_count": len(diagnoses),
        "intervention_outcomes_count": len(outcomes),
    }
