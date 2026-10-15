from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(default="Python Learner", min_length=2, max_length=255)
    role: str = Field(default="student")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("Please provide a valid email address.")
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"student", "educator", "admin"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {sorted(allowed)}")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class PreferenceUpdateRequest(BaseModel):
    selected_course_id: Optional[int] = None
    language: str = Field(default="en", pattern="^(en|hi|bilingual)$")
    text_size: str = Field(default="normal", pattern="^(normal|large|xlarge)$")
    reduced_motion: bool = False
    high_contrast: bool = False
    plain_language_mode: bool = False
    preferred_formats: list[str] = Field(
        default_factory=lambda: ["text", "diagram", "interactive", "audio"]
    )
    daily_goal_minutes: int = Field(default=20, ge=5, le=180)
    streak_opt_in: bool = True
    onboarding_completed: bool = True


class AttemptSubmitRequest(BaseModel):
    question_id: int = Field(..., gt=0)
    response: str = Field(..., min_length=1, max_length=512)
    hints_used: int = Field(default=0, ge=0, le=10)
    attempt_context: str = Field(default="practice")


class DiagnosticFollowupSubmitRequest(BaseModel):
    followup_question_id: int = Field(..., gt=0)
    response: str = Field(..., min_length=1, max_length=512)


class InterventionCompleteRequest(BaseModel):
    completion_seconds: Optional[int] = Field(default=120, ge=1, le=7200)
    format_used: Optional[str] = Field(default="multimodal")
    interactive_check_answer: Optional[str] = None


class InterventionVerifyRequest(BaseModel):
    verification_question_id: int = Field(..., gt=0)
    response: str = Field(..., min_length=1, max_length=512)
    completion_seconds: Optional[int] = Field(default=90, ge=1, le=7200)


class EducatorNoteRequest(BaseModel):
    outcome_id: int = Field(..., gt=0)
    educator_note: str = Field(..., min_length=2, max_length=1000)
    acknowledged: bool = True


class AdminConceptCreateRequest(BaseModel):
    course_id: int = Field(..., gt=0)
    slug: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=255)
    description: str = Field(..., min_length=5)
    learning_objective: str = Field(..., min_length=5)
    order_index: int = Field(default=1, ge=1, le=100)
    prior_mastery: float = Field(default=0.35, ge=0.0, le=1.0)
    prerequisite_ids: list[int] = Field(default_factory=list)


class AdminOptionInput(BaseModel):
    option_key: str = Field(..., min_length=1, max_length=16)
    option_text: str = Field(..., min_length=1)
    misconception_id: Optional[int] = None
    secondary_misconception_id: Optional[int] = None
    confidence_weight: float = Field(default=0.80, ge=0.1, le=1.0)
    ambiguity_note: Optional[str] = None
    is_correct: bool = False


class AdminQuestionCreateRequest(BaseModel):
    stable_id: str = Field(..., min_length=3, max_length=100)
    concept_id: int = Field(..., gt=0)
    difficulty: int = Field(default=1, ge=1, le=3)
    question_type: str = Field(default="multiple_choice")
    is_verification_only: bool = False
    is_diagnostic_followup: bool = False
    target_misconception_codes: list[str] = Field(default_factory=list)
    content: str = Field(..., min_length=5)
    code_snippet: Optional[str] = None
    answer_key: str = Field(..., min_length=1, max_length=255)
    explanation: str = Field(..., min_length=5)
    plain_language_explanation: Optional[str] = None
    worked_example: Optional[str] = None
    hint_ladder: list[str] = Field(default_factory=list)
    diagram_svg: Optional[str] = None
    audio_transcript: Optional[str] = None
    version: str = Field(default="1.0.0")
    status: str = Field(default="published")
    options: list[AdminOptionInput] = Field(default_factory=list)


class AdminQuestionUpdateRequest(BaseModel):
    content: Optional[str] = None
    code_snippet: Optional[str] = None
    answer_key: Optional[str] = None
    explanation: Optional[str] = None
    plain_language_explanation: Optional[str] = None
    worked_example: Optional[str] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=3)
    status: Optional[str] = None
    version: Optional[str] = None
    hint_ladder: Optional[list[str]] = None


class AdminMisconceptionCreateRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=100)
    concept_id: int = Field(..., gt=0)
    label: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    diagnostic_rule: str = Field(..., min_length=3)
    remediation_focus: str = Field(default="")
    rule_version: str = Field(default="v1.1.0-rules")
    status: str = Field(default="active")


class AdminActivityCreateRequest(BaseModel):
    stable_id: str = Field(..., min_length=3, max_length=100)
    concept_id: int = Field(..., gt=0)
    target_misconception_id: Optional[int] = None
    title: str = Field(..., min_length=3, max_length=255)
    activity_type: str = Field(default="targeted_remediation")
    difficulty: int = Field(default=1, ge=1, le=3)
    content_ref: str = Field(default="curated-python-v1")
    content_body: str = Field(..., min_length=10)
    plain_language_body: Optional[str] = None
    code_example: Optional[str] = None
    diagram_svg: Optional[str] = None
    audio_transcript: Optional[str] = None
    interactive_exercise: Optional[dict[str, Any]] = None
    format: str = Field(default="multimodal")
    estimated_duration: int = Field(default=6, ge=1, le=120)
    version: str = Field(default="1.0.0")
    status: str = Field(default="published")
