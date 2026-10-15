from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False, default="Learner")
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="student", index=True)
    status = Column(String(32), nullable=False, default="active")
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    selected_course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    points = Column(Integer, nullable=False, default=0)
    current_streak = Column(Integer, nullable=False, default=0)
    daily_goal_minutes = Column(Integer, nullable=False, default=20)
    streak_opt_in = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("role IN ('student', 'educator', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'suspended', 'deleted')", name="ck_users_status"),
    )

    preferences = relationship(
        "LearnerPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    attempts = relationship("Attempt", back_populates="user", cascade="all, delete-orphan")
    mastery_states = relationship("MasteryState", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    user_achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")


class LearnerPreference(Base):
    __tablename__ = "learner_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    language = Column(String(32), nullable=False, default="en")
    text_size = Column(String(32), nullable=False, default="normal")
    reduced_motion = Column(Boolean, nullable=False, default=False)
    high_contrast = Column(Boolean, nullable=False, default=False)
    plain_language_mode = Column(Boolean, nullable=False, default=False)
    preferred_formats = Column(JSON, nullable=False, default=lambda: ["text", "diagram", "interactive"])
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="preferences")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="published", index=True)
    version = Column(String(32), nullable=False, default="1.0.0")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    concepts = relationship("Concept", back_populates="course", cascade="all, delete-orphan")


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    learning_objective = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False, default=1)
    prior_mastery = Column(Float, nullable=False, default=0.35)
    status = Column(String(32), nullable=False, default="published")

    course = relationship("Course", back_populates="concepts")
    questions = relationship("Question", back_populates="concept", cascade="all, delete-orphan")
    misconceptions = relationship("Misconception", back_populates="concept", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="concept", cascade="all, delete-orphan")


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"

    id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    prerequisite_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("concept_id", "prerequisite_id", name="uq_concept_prerequisite"),
        CheckConstraint("concept_id != prerequisite_id", name="ck_no_self_prerequisite"),
    )


class Misconception(Base):
    __tablename__ = "misconceptions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    diagnostic_rule = Column(Text, nullable=False)
    remediation_focus = Column(Text, nullable=False, default="")
    rule_version = Column(String(64), nullable=False, default="v1.0.0-rules")
    status = Column(String(32), nullable=False, default="active")

    concept = relationship("Concept", back_populates="misconceptions")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    stable_id = Column(String(100), unique=True, nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    difficulty = Column(Integer, nullable=False, default=1)
    question_type = Column(String(64), nullable=False, default="multiple_choice")
    is_verification_only = Column(Boolean, nullable=False, default=False)
    is_diagnostic_followup = Column(Boolean, nullable=False, default=False)
    target_misconception_codes = Column(JSON, nullable=False, default=list)
    content = Column(Text, nullable=False)
    code_snippet = Column(Text, nullable=True)
    answer_key = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    plain_language_explanation = Column(Text, nullable=True)
    worked_example = Column(Text, nullable=True)
    hint_ladder = Column(JSON, nullable=False, default=list)
    diagram_svg = Column(Text, nullable=True)
    audio_transcript = Column(Text, nullable=True)
    version = Column(String(32), nullable=False, default="1.0.0")
    status = Column(String(32), nullable=False, default="published", index=True)

    __table_args__ = (
        CheckConstraint("difficulty >= 1 AND difficulty <= 3", name="ck_question_difficulty"),
    )

    concept = relationship("Concept", back_populates="questions")
    answer_options = relationship(
        "AnswerOption", back_populates="question", cascade="all, delete-orphan"
    )


class AnswerOption(Base):
    __tablename__ = "answer_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_key = Column(String(16), nullable=False)
    option_text = Column(Text, nullable=False)
    misconception_id = Column(Integer, ForeignKey("misconceptions.id", ondelete="SET NULL"), nullable=True, index=True)
    secondary_misconception_id = Column(
        Integer, ForeignKey("misconceptions.id", ondelete="SET NULL"), nullable=True
    )
    confidence_weight = Column(Float, nullable=False, default=0.80)
    ambiguity_note = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)

    question = relationship("Question", back_populates="answer_options")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    stable_id = Column(String(100), unique=True, nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    target_misconception_id = Column(
        Integer, ForeignKey("misconceptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(255), nullable=False)
    activity_type = Column(String(64), nullable=False, default="targeted_remediation")
    difficulty = Column(Integer, nullable=False, default=1)
    content_ref = Column(String(255), nullable=False)
    content_body = Column(Text, nullable=False)
    plain_language_body = Column(Text, nullable=True)
    code_example = Column(Text, nullable=True)
    diagram_svg = Column(Text, nullable=True)
    audio_transcript = Column(Text, nullable=True)
    interactive_exercise = Column(JSON, nullable=True)
    format = Column(String(64), nullable=False, default="multimodal")
    estimated_duration = Column(Integer, nullable=False, default=5)
    version = Column(String(32), nullable=False, default="1.0.0")
    status = Column(String(32), nullable=False, default="published", index=True)

    concept = relationship("Concept", back_populates="activities")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    response = Column(String(512), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    hints_used = Column(Integer, nullable=False, default=0)
    attempt_context = Column(String(64), nullable=False, default="practice")
    started_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = relationship("User", back_populates="attempts")
    diagnoses = relationship("Diagnosis", back_populates="attempt", foreign_keys="Diagnosis.attempt_id")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    misconception_id = Column(
        Integer, ForeignKey("misconceptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_misconceptions = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.0)
    evidence = Column(Text, nullable=False)
    status = Column(String(64), nullable=False, default="insufficient_evidence", index=True)
    followup_question_id = Column(
        Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True
    )
    followup_attempt_id = Column(
        Integer, ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )
    rule_version = Column(String(64), nullable=False, default="v1.0.0-rules")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    attempt = relationship("Attempt", back_populates="diagnoses", foreign_keys=[attempt_id])


class MasteryState(Base):
    __tablename__ = "mastery_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    mastery = Column(Float, nullable=False, default=0.35)
    attempts_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    uncertainty = Column(Float, nullable=False, default=0.50)
    uncertainty_or_evidence = Column(Text, nullable=False, default="Prior estimate (no attempts yet)")
    last_alpha = Column(Float, nullable=False, default=0.20)
    model_version = Column(String(64), nullable=False, default="v1.0.0-ema-alpha0.2")
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uq_user_concept_mastery"),
        CheckConstraint("mastery >= 0.0 AND mastery <= 1.0", name="ck_mastery_bounds"),
    )

    user = relationship("User", back_populates="mastery_states")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_attempt_id = Column(
        Integer, ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )
    trigger_diagnosis_id = Column(
        Integer, ForeignKey("diagnoses.id", ondelete="SET NULL"), nullable=True
    )
    strategy = Column(String(64), nullable=False, default="proposed")
    total_score = Column(Float, nullable=False, default=0.0)
    score_components = Column(JSON, nullable=False, default=dict)
    reason = Column(Text, nullable=False)
    rank = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="pending", index=True)
    rule_version = Column(String(64), nullable=False, default="v1.0.0-rules")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="recommendations")


class InterventionOutcome(Base):
    __tablename__ = "intervention_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(
        Integer, ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    pre_attempt_id = Column(Integer, ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True)
    followup_attempt_id = Column(
        Integer, ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )
    verification_question_id = Column(
        Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True
    )
    pre_mastery = Column(Float, nullable=False, default=0.35)
    post_mastery = Column(Float, nullable=False, default=0.35)
    immediate_outcome = Column(String(64), nullable=False, default="pending")
    error_recurred = Column(Boolean, nullable=False, default=False)
    original_misconception_id = Column(
        Integer, ForeignKey("misconceptions.id", ondelete="SET NULL"), nullable=True
    )
    post_misconception_id = Column(
        Integer, ForeignKey("misconceptions.id", ondelete="SET NULL"), nullable=True
    )
    completion_seconds = Column(Integer, nullable=True)
    educator_note = Column(Text, nullable=True)
    educator_Acknowledged = Column(Boolean, nullable=False, default=False)
    rule_version = Column(String(64), nullable=False, default="v1.0.0-rules")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, default="milestone")
    points_reward = Column(Integer, nullable=False, default=25)
    criteria = Column(JSON, nullable=False, default=dict)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id = Column(
        Integer, ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    earned_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )

    user = relationship("User", back_populates="user_achievements")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_role = Column(String(32), nullable=True)
    action = Column(String(128), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=True)
    rule_version = Column(String(64), nullable=False, default="v1.0.0-rules")
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


Index("ix_attempts_user_question", Attempt.user_id, Attempt.question_id)
Index("ix_diagnoses_user_concept", Diagnosis.user_id, Diagnosis.concept_id)
Index("ix_recommendations_user_status", Recommendation.user_id, Recommendation.status)


class EducatorCourseAssignment(Base):
    """Explicit authorization linking an educator to a course/cohort."""

    __tablename__ = "educator_course_assignments"

    id = Column(Integer, primary_key=True, index=True)
    educator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint("educator_id", "course_id", name="uq_educator_course_assignment"),)
