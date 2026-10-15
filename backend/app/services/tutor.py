from typing import Optional
from app.core.config import settings
from app.models.entities import Misconception, Question


class LLMProviderAdapter:
    """
    Server-side adapter for optional LLM-enhanced tutoring explanations.
    Safeguards:
    - Core product works 100% deterministically without an API key.
    - Never exposes secrets to the client.
    - Always grounds output in curated question explanations and falls back safely on any error.
    """

    def __init__(self):
        self.provider = (settings.LLM_PROVIDER or "none").lower()
        self.api_key = settings.LLM_API_KEY or ""

    @property
    def is_enabled(self) -> bool:
        return self.provider not in ("none", "", "disabled") and bool(self.api_key)

    def build_grounded_tutor_response(
        self,
        question: Question,
        misconception: Optional[Misconception] = None,
        plain_language: bool = False,
    ) -> dict:
        base_explanation = (
            question.plain_language_explanation
            if (plain_language and question.plain_language_explanation)
            else question.explanation
        )
        misconception_guidance = None
        if misconception:
            misconception_guidance = (
                f"Common pattern to watch for ({misconception.label}): "
                f"{misconception.description} "
                f"Tip: {misconception.remediation_focus}"
            )

        # Safe fallback / default deterministic curated tutor
        return {
            "source": "curated_content",
            "llm_used": False,
            "authoritative_answer_key": question.answer_key,
            "explanation": base_explanation,
            "plain_language_explanation": question.plain_language_explanation or question.explanation,
            "worked_example": question.worked_example,
            "misconception_guidance": misconception_guidance,
            "hint_ladder": question.hint_ladder or [],
            "grounding_reference": f"Curated Question Bank ID: {question.stable_id} (v{question.version})",
        }


tutor_adapter = LLMProviderAdapter()


def get_hint_for_question(question: Question, hint_index: int = 0) -> dict:
    """
    Returns one step from the progressive hint ladder without immediately revealing
    the full solution unless the learner has stepped through the hints.
    """
    hints = list(question.hint_ladder or [])
    if not hints:
        hints = [
            "Read the question prompt carefully and trace each line step by step.",
            "Check the data types and values of variables before the final line executes.",
        ]
    clamped_idx = max(0, min(len(hints) - 1, hint_index))
    return {
        "question_id": question.id,
        "stable_id": question.stable_id,
        "hint_index": clamped_idx,
        "total_hints": len(hints),
        "hint_text": hints[clamped_idx],
        "has_more_hints": clamped_idx < len(hints) - 1,
        "worked_example": question.worked_example if clamped_idx == len(hints) - 1 else None,
        "source": "curated_content",
    }
