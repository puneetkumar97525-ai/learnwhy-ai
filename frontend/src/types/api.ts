export interface UserPreferences {
  language: 'en' | 'hi' | 'bilingual';
  text_size: 'normal' | 'large' | 'xlarge';
  reduced_motion: boolean;
  high_contrast: boolean;
  plain_language_mode: boolean;
  preferred_formats: string[];
}

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: 'student' | 'educator' | 'admin';
  status: string;
  onboarding_completed: boolean;
  selected_course_id: number | null;
  points: number;
  current_streak: number;
  daily_goal_minutes: number;
  streak_opt_in: boolean;
  preferences: UserPreferences;
}

export interface ConceptNode {
  id: number;
  course_id: number;
  slug: string;
  name: string;
  description: string;
  learning_objective: string;
  order_index: number;
  prerequisite_ids: number[];
  dependent_ids: number[];
  prerequisites_ready: boolean;
  mastery: number;
  mastery_percent: number;
  attempts_count: number;
  correct_count: number;
  uncertainty: number;
  status_label: string;
  evidence_note: string;
  questions_count: number;
}

export interface QuestionOption {
  id: number;
  option_key: string;
  option_text: string;
}

export interface LearnerQuestion {
  id: number;
  stable_id: string;
  concept_id: number;
  concept_name: string;
  difficulty: number;
  difficulty_label: string;
  question_type: string;
  is_verification_only: boolean;
  is_diagnostic_followup: boolean;
  content: string;
  code_snippet?: string | null;
  diagram_svg?: string | null;
  audio_transcript?: string | null;
  total_hints: number;
  version: string;
  options: QuestionOption[];
}

export interface CandidateMisconception {
  id: number;
  code: string;
  label: string;
  probability: number;
}

export interface DiagnosisResult {
  id: number;
  status:
    | 'correct_no_error'
    | 'diagnosed'
    | 'ambiguous_followup_needed'
    | 'insufficient_evidence'
    | 'resolved_by_followup';
  confidence: number;
  evidence: string;
  rule_version: string;
  misconception?: {
    id: number;
    code: string;
    label: string;
    description: string;
  } | null;
  candidate_misconceptions: CandidateMisconception[];
  requires_diagnostic_followup?: boolean;
  followup_question?: LearnerQuestion | null;
}

export interface TutorFeedback {
  source: string;
  llm_used: boolean;
  authoritative_answer_key: string;
  explanation: string;
  plain_language_explanation: string;
  worked_example?: string | null;
  misconception_guidance?: string | null;
  hint_ladder: string[];
  grounding_reference: string;
}

export interface LearningActivity {
  id: number;
  stable_id: string;
  concept_id: number;
  concept_name: string;
  target_misconception_id?: number | null;
  target_misconception_label?: string | null;
  title: string;
  activity_type: string;
  difficulty: number;
  content_ref: string;
  content_body: string;
  plain_language_body: string;
  code_example?: string | null;
  diagram_svg?: string | null;
  audio_transcript?: string | null;
  interactive_exercise?: {
    prompt: string;
    expected_answer: string;
    hint: string;
  } | null;
  format: string;
  estimated_duration: number;
  version: string;
}

export interface ScoreComponents {
  gap_relevance: number;
  prerequisite_importance: number;
  difficulty_fit: number;
  weights: {
    gap_relevance: number;
    prerequisite_importance: number;
    difficulty_fit: number;
  };
  formula: string;
  concept_mastery_estimate: number;
  targets_diagnosed_misconception: boolean;
  targeted_misconception_code?: string;
  targeted_misconception_label?: string;
  prerequisites_ready?: boolean;
}

export interface RecommendationItem {
  id: number;
  rank: number;
  strategy: string;
  status: string;
  total_score: number;
  score_components: ScoreComponents;
  reason: string;
  rule_version: string;
  created_at?: string;
  activity: LearningActivity;
}
