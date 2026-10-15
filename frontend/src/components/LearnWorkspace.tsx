import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Code2,
  FileText,
  HelpCircle,
  Lightbulb,
  Play,
  RefreshCw,
  Sparkles,
  Volume2,
  XCircle,
} from 'lucide-react';
import { api } from '../services/api';
import {
  LearnerQuestion,
  RecommendationItem,
  UserProfile,
} from '../types/api';

interface LearnWorkspaceProps {
  user: UserProfile;
  initialConceptId?: number | null;
  initialRecommendation?: RecommendationItem | null;
  onUserPointsUpdated: () => void;
}

type Stage = 'question' | 'intervention' | 'verification';

export const LearnWorkspace: React.FC<LearnWorkspaceProps> = ({
  user,
  initialConceptId,
  initialRecommendation,
  onUserPointsUpdated,
}) => {
  const [stage, setStage] = useState<Stage>(
    initialRecommendation ? 'intervention' : 'question'
  );
  const [selectedConceptId, setSelectedConceptId] = useState<number | null>(
    initialConceptId || null
  );
  const [question, setQuestion] = useState<LearnerQuestion | null>(null);
  const [adaptiveReason, setAdaptiveReason] = useState<string>('');
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [hints, setHints] = useState<string[]>([]);
  const [hintLoading, setHintLoading] = useState(false);
  const [attemptResult, setAttemptResult] = useState<any | null>(null);

  // Follow-up state
  const [followupChoice, setFollowupChoice] = useState<string>('');
  const [followupResult, setFollowupResult] = useState<any | null>(null);
  const [followupSubmitting, setFollowupSubmitting] = useState(false);

  // Intervention & Verification state
  const [activeRec, setActiveRec] = useState<RecommendationItem | null>(
    initialRecommendation || null
  );
  const [activeFormatTab, setActiveFormatTab] = useState<
    'all' | 'text' | 'diagram' | 'interactive' | 'audio'
  >('all');
  const [microCheckAnswer, setMicroCheckAnswer] = useState('');
  const [microCheckFeedback, setMicroCheckFeedback] = useState<string | null>(
    null
  );
  const [verificationQuestion, setVerificationQuestion] =
    useState<LearnerQuestion | null>(null);
  const [verificationChoice, setVerificationChoice] = useState<string>('');
  const [verificationResult, setVerificationResult] = useState<any | null>(
    null
  );

  // Audio narration state
  const [showTranscript, setShowTranscript] = useState<boolean>(true);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadQuestion = async (
    conceptId?: number | null,
    excludeQId?: number | null
  ) => {
    setLoading(true);
    setError(null);
    setAttemptResult(null);
    setFollowupResult(null);
    setFollowupChoice('');
    setSelectedOption('');
    setHints([]);
    setStage('question');
    try {
      const res = await api.getNextQuestion(conceptId, excludeQId);
      setQuestion(res.question);
      setAdaptiveReason(res.adaptive_selection_reason || '');
    } catch (err: any) {
      setError(err?.message || 'Unable to load practice question.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialRecommendation) {
      setActiveRec(initialRecommendation);
      setStage('intervention');
    } else {
      loadQuestion(initialConceptId || null, null);
    }
  }, [initialConceptId, initialRecommendation]);

  const handleRequestHint = async () => {
    if (!question) return;
    setHintLoading(true);
    try {
      const nextIndex = hints.length;
      const res = await api.getQuestionHint(question.id, nextIndex);
      if (res.hint_text && !hints.includes(res.hint_text)) {
        setHints((prev) => [...prev, res.hint_text]);
      }
    } catch {
      // ignore
    } finally {
      setHintLoading(false);
    }
  };

  const handleSubmitAttempt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question || !selectedOption) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.submitAttempt(
        question.id,
        selectedOption,
        hints.length
      );
      setAttemptResult(res);
      onUserPointsUpdated();
    } catch (err: any) {
      setError(err?.message || 'Could not submit answer.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitFollowup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !attemptResult ||
      !attemptResult.diagnosis?.followup_question ||
      !followupChoice
    )
      return;
    setFollowupSubmitting(true);
    try {
      const fq = attemptResult.diagnosis.followup_question;
      const res = await api.submitDiagnosticFollowup(
        attemptResult.attempt_id,
        fq.id,
        followupChoice
      );
      setFollowupResult(res);
      // Update attemptResult's diagnosis and recommended_next with the disambiguated result
      setAttemptResult((prev: any) => ({
        ...prev,
        diagnosis: {
          ...res.diagnosis,
          requires_diagnostic_followup: false,
          followup_question: fq,
        },
        recommended_next: res.recommended_next || prev.recommended_next,
      }));
      onUserPointsUpdated();
    } catch (err: any) {
      setError(err?.message || 'Failed to submit diagnostic follow-up.');
    } finally {
      setFollowupSubmitting(false);
    }
  };

  const handleOpenInterventionFromAttempt = () => {
    const recPayload = attemptResult?.recommended_next;
    if (!recPayload) return;
    const mappedRec: RecommendationItem = {
      id: recPayload.recommendation_id,
      rank: 1,
      strategy: 'proposed',
      status: 'in_progress',
      total_score: recPayload.total_score,
      score_components: recPayload.score_components,
      reason: recPayload.reason,
      rule_version: recPayload.rule_version,
      activity: recPayload.activity,
    };
    setActiveRec(mappedRec);
    setMicroCheckAnswer('');
    setMicroCheckFeedback(null);
    setVerificationResult(null);
    setStage('intervention');
  };

  const handleCompleteIntervention = async () => {
    if (!activeRec) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.completeIntervention(
        activeRec.id,
        120,
        activeFormatTab
      );
      setVerificationQuestion(res.verification_question);
      setVerificationChoice('');
      setVerificationResult(null);
      setStage('verification');
      onUserPointsUpdated();
    } catch (err: any) {
      setError(err?.message || 'Could not start verification step.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeRec || !verificationQuestion || !verificationChoice) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.verifyIntervention(
        activeRec.id,
        verificationQuestion.id,
        verificationChoice,
        75
      );
      setVerificationResult(res);
      onUserPointsUpdated();
    } catch (err: any) {
      setError(err?.message || 'Could not verify answer.');
    } finally {
      setLoading(false);
    }
  };

  const handleSpeakText = (textToSpeak: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setShowTranscript(true);
      return;
    }
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 0.95;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="space-y-6">
      {/* Learning Loop Stepper Banner */}
      <nav
        aria-label="Transparent learning loop progress"
        className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hc-card flex flex-wrap items-center justify-between gap-4"
      >
        <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm font-semibold">
          <span
            className={`px-3 py-1.5 rounded-lg border ${
              stage === 'question'
                ? 'bg-indigo-700 text-white border-indigo-700'
                : 'bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            1. Diagnose &amp; Follow-Up
          </span>
          <span className="text-slate-400">&rarr;</span>
          <span
            className={`px-3 py-1.5 rounded-lg border ${
              stage === 'intervention'
                ? 'bg-indigo-700 text-white border-indigo-700'
                : 'bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            2. Multimodal Remediation
          </span>
          <span className="text-slate-400">&rarr;</span>
          <span
            className={`px-3 py-1.5 rounded-lg border ${
              stage === 'verification'
                ? 'bg-indigo-700 text-white border-indigo-700'
                : 'bg-slate-100 text-slate-700 border-slate-300'
            }`}
          >
            3. Fresh Verification &amp; Mastery Update
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => loadQuestion(selectedConceptId, question?.id || null)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-800"
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Load Another Question</span>
          </button>
        </div>
      </nav>

      {error && (
        <div
          role="alert"
          className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-sm font-medium"
        >
          {error}
        </div>
      )}

      {/* STAGE 1: QUESTION & DIAGNOSTIC WORKSPACE */}
      {stage === 'question' && question && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Question Column */}
          <section
            aria-labelledby="question-heading"
            className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-900 border border-indigo-200">
                  {question.concept_name}
                </span>
                <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 text-slate-800 border border-slate-300">
                  Level {question.difficulty}: {question.difficulty_label}
                </span>
                <span className="text-xs font-mono text-slate-600">
                  ID: {question.stable_id}
                </span>
              </div>

              {question.audio_transcript && (
                <button
                  type="button"
                  onClick={() =>
                    handleSpeakText(
                      `${question.content}. ${question.audio_transcript}`
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-800"
                >
                  <Volume2 className="w-3.5 h-3.5 text-indigo-700" aria-hidden="true" />
                  <span>{isSpeaking ? 'Stop Audio' : 'Read Aloud'}</span>
                </button>
              )}
            </div>

            {adaptiveReason && (
              <p className="text-xs text-slate-600 bg-slate-50 px-3 py-2 rounded-lg border border-slate-200">
                <strong>Adaptive Selection:</strong> {adaptiveReason}
              </p>
            )}

            <h2
              id="question-heading"
              className="text-lg sm:text-xl font-bold text-slate-900 leading-snug"
            >
              {question.content}
            </h2>

            {question.code_snippet && (
              <div className="rounded-xl bg-slate-900 text-slate-100 p-4 font-mono text-sm overflow-x-auto border border-slate-800">
                <pre className="leading-relaxed">
                  <code>{question.code_snippet}</code>
                </pre>
              </div>
            )}

            {question.diagram_svg && (
              <div className="rounded-xl bg-slate-50 border border-slate-200 p-3 overflow-x-auto">
                <div className="text-xs font-semibold text-slate-700 mb-2">
                  Visual Concept Diagram:
                </div>
                <div
                  dangerouslySetInnerHTML={{ __html: question.diagram_svg }}
                />
              </div>
            )}

            {question.audio_transcript && showTranscript && (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700">
                <span className="font-semibold text-slate-900">
                  Audio / Screen-Reader Transcript:{' '}
                </span>
                {question.audio_transcript}
              </div>
            )}

            <form onSubmit={handleSubmitAttempt} className="space-y-4">
              <fieldset className="space-y-2.5">
                <legend className="text-sm font-semibold text-slate-800 mb-2">
                  Select your answer (Keyboard operable):
                </legend>
                {question.options.map((opt) => {
                  const isSelected = selectedOption === opt.option_key;
                  return (
                    <label
                      key={opt.id}
                      htmlFor={`q-opt-${opt.option_key}`}
                      className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-indigo-50 border-indigo-600 text-indigo-950 font-semibold'
                          : 'bg-white border-slate-300 hover:bg-slate-50 text-slate-900'
                      }`}
                    >
                      <input
                        id={`q-opt-${opt.option_key}`}
                        type="radio"
                        name="learner-answer"
                        value={opt.option_key}
                        checked={isSelected}
                        onChange={() => setSelectedOption(opt.option_key)}
                        className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-600"
                      />
                      <span className="text-sm leading-relaxed">
                        <strong className="font-mono mr-2">{opt.option_key}.</strong>
                        {opt.option_text}
                      </span>
                    </label>
                  );
                })}
              </fieldset>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleRequestHint}
                  disabled={
                    hintLoading || hints.length >= (question.total_hints || 3)
                  }
                  className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-amber-400 bg-amber-50 hover:bg-amber-100 disabled:opacity-60 text-amber-950 font-semibold text-xs transition-colors"
                >
                  <Lightbulb className="w-4 h-4 text-amber-700" aria-hidden="true" />
                  <span>
                    {hints.length === 0
                      ? `Request Hint (1/${question.total_hints || 3})`
                      : hints.length < (question.total_hints || 3)
                      ? `Next Hint (${hints.length + 1}/${question.total_hints || 3})`
                      : 'All Hints Shown'}
                  </span>
                </button>

                <button
                  type="submit"
                  disabled={!selectedOption || loading}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-700 hover:bg-indigo-800 disabled:opacity-50 text-white font-semibold text-sm shadow-sm transition-colors"
                >
                  <span>{loading ? 'Checking...' : 'Submit Answer'}</span>
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </form>

            {/* Progressive Hint Ladder Panel */}
            {hints.length > 0 && (
              <div
                role="region"
                aria-label="Tutor hint ladder"
                className="p-4 rounded-xl bg-amber-50/80 border border-amber-300 space-y-2"
              >
                <div className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
                  <Lightbulb className="w-4 h-4 text-amber-700" aria-hidden="true" />
                  <span>Curated Tutor Hint Ladder (No point penalty)</span>
                </div>
                <ol className="list-decimal list-inside space-y-1.5 text-sm text-amber-950">
                  {hints.map((h, i) => (
                    <li key={i} className="leading-relaxed">
                      {h}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </section>

          {/* Right Column: Tutor Feedback, Mastery Update & Misconception Diagnosis */}
          <aside
            aria-label="Tutor feedback and misconception diagnosis"
            aria-live="polite"
            className="lg:col-span-5 space-y-5"
          >
            {!attemptResult ? (
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-3">
                <div className="flex items-center gap-2 text-indigo-800 font-bold text-base">
                  <Sparkles className="w-5 h-5" aria-hidden="true" />
                  <span>Intelligent Tutor &amp; Diagnostic Engine</span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Submit an answer on the left—or request a progressive hint first. LearnWhy AI will:
                </p>
                <ul className="text-xs text-slate-700 space-y-2 list-disc list-inside">
                  <li>
                    Verify correctness against the deterministic, curated answer key.
                  </li>
                  <li>
                    Update only <strong>{question.concept_name}</strong> mastery using{' '}
                    <code className="bg-slate-100 px-1 py-0.5 rounded">
                      M_new = (1 - α)*M_old + α*y
                    </code>
                    .
                  </li>
                  <li>
                    Check if a wrong answer matches a specific misconception rule, or ask a <strong>diagnostic follow-up</strong> if multiple causes are plausible.
                  </li>
                </ul>
              </div>
            ) : (
              <div className="space-y-5">
                {/* 1. Correctness & Authoritative Explanation Card */}
                <div
                  className={`rounded-2xl p-5 border shadow-sm space-y-3 ${
                    attemptResult.is_correct
                      ? 'bg-emerald-50/90 border-emerald-400 text-emerald-950'
                      : 'bg-amber-50/90 border-amber-400 text-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 font-bold text-base">
                      {attemptResult.is_correct ? (
                        <CheckCircle2
                          className="w-5 h-5 text-emerald-700 shrink-0"
                          aria-hidden="true"
                        />
                      ) : (
                        <AlertTriangle
                          className="w-5 h-5 text-amber-700 shrink-0"
                          aria-hidden="true"
                        />
                      )}
                      <span>{attemptResult.status_badge}</span>
                    </div>
                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-white border border-slate-300">
                      Answer Key: {attemptResult.tutor.authoritative_answer_key}
                    </span>
                  </div>

                  <p className="text-sm leading-relaxed">
                    {user.preferences?.plain_language_mode
                      ? attemptResult.tutor.plain_language_explanation
                      : attemptResult.tutor.explanation}
                  </p>

                  {attemptResult.tutor.worked_example && (
                    <div className="rounded-xl bg-slate-900 text-slate-100 p-3 font-mono text-xs overflow-x-auto">
                      <div className="text-slate-400 mb-1">Worked Example:</div>
                      <pre>{attemptResult.tutor.worked_example}</pre>
                    </div>
                  )}

                  <div className="text-[11px] text-slate-600 flex items-center justify-between pt-1">
                    <span>{attemptResult.tutor.grounding_reference}</span>
                    <span>Source: Deterministic Curated Tutor</span>
                  </div>
                </div>

                {/* 2. Transparent Misconception Diagnosis Card */}
                <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hc-card space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-bold text-sm text-slate-900 uppercase tracking-wider">
                      Misconception Diagnosis
                    </h3>
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-900 border border-indigo-200">
                      Status: {attemptResult.diagnosis.status} (Conf:{' '}
                      {Math.round(attemptResult.diagnosis.confidence * 100)}%)
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-200">
                    {attemptResult.diagnosis.evidence}
                  </p>

                  {attemptResult.diagnosis.misconception && (
                    <div className="p-3 rounded-xl bg-indigo-50/70 border border-indigo-200 text-xs space-y-1">
                      <div className="font-bold text-indigo-950">
                        Candidate Pattern [{attemptResult.diagnosis.misconception.code}]:{' '}
                        {attemptResult.diagnosis.misconception.label}
                      </div>
                      <div className="text-slate-700">
                        {attemptResult.diagnosis.misconception.description}
                      </div>
                    </div>
                  )}

                  {/* Ambiguous Diagnosis Follow-Up Probe */}
                  {attemptResult.diagnosis.requires_diagnostic_followup &&
                    attemptResult.diagnosis.followup_question && (
                      <div className="p-4 rounded-xl bg-amber-50 border-2 border-amber-400 space-y-3">
                        <div className="flex items-center gap-2 text-amber-950 font-bold text-sm">
                          <HelpCircle className="w-4 h-4 text-amber-800 shrink-0" aria-hidden="true" />
                          <span>
                            Ambiguous Evidence — Quick Diagnostic Follow-Up
                          </span>
                        </div>
                        <p className="text-xs text-amber-900">
                          Multiple causes are plausible (
                          {attemptResult.diagnosis.candidate_misconceptions
                            .map((c: any) => c.label)
                            .join(' OR ')}
                          ). Answer this 15-second probe so we recommend the right remediation:
                        </p>
                        <div className="text-sm font-semibold text-slate-900">
                          {attemptResult.diagnosis.followup_question.content}
                        </div>
                        {attemptResult.diagnosis.followup_question.code_snippet && (
                          <pre className="p-2.5 rounded-lg bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto">
                            {attemptResult.diagnosis.followup_question.code_snippet}
                          </pre>
                        )}
                        <form onSubmit={handleSubmitFollowup} className="space-y-2">
                          {attemptResult.diagnosis.followup_question.options.map(
                            (fOpt: any) => (
                              <label
                                key={fOpt.id}
                                className="flex items-center gap-2.5 p-2.5 rounded-lg bg-white border border-amber-300 text-xs cursor-pointer"
                              >
                                <input
                                  type="radio"
                                  name="followup-option"
                                  value={fOpt.option_key}
                                  checked={followupChoice === fOpt.option_key}
                                  onChange={() => setFollowupChoice(fOpt.option_key)}
                                />
                                <span>
                                  <strong className="font-mono">{fOpt.option_key}.</strong>{' '}
                                  {fOpt.option_text}
                                </span>
                              </label>
                            )
                          )}
                          <button
                            type="submit"
                            disabled={!followupChoice || followupSubmitting}
                            className="w-full py-2 px-3 rounded-lg bg-amber-800 hover:bg-amber-900 text-white font-semibold text-xs"
                          >
                            {followupSubmitting
                              ? 'Updating Diagnosis...'
                              : 'Submit Diagnostic Follow-Up'}
                          </button>
                        </form>
                      </div>
                    )}

                  {followupResult && (
                    <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-xs text-emerald-950">
                      <strong>Follow-up Resolved:</strong>{' '}
                      {followupResult.followup_explanation}
                    </div>
                  )}
                </div>

                {/* 3. Concept Mastery Update Card */}
                <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hc-card space-y-2">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Concept Mastery Estimate Updated
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-slate-900">
                      {attemptResult.mastery_update.concept_name}
                    </span>
                    <span className="font-mono font-bold text-sm text-indigo-800">
                      {Math.round(attemptResult.mastery_update.previous_mastery * 100)}% &rarr;{' '}
                      {Math.round(attemptResult.mastery_update.new_mastery * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">
                    {attemptResult.mastery_update.evidence_note}
                  </p>
                </div>

                {/* 4. Next Recommended Remediation Action */}
                {attemptResult.recommended_next && (
                  <div className="bg-indigo-950 text-white rounded-2xl p-5 border border-indigo-800 shadow-sm space-y-3">
                    <div className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                      Recommended Targeted Intervention (Score R ={' '}
                      {attemptResult.recommended_next.total_score.toFixed(2)})
                    </div>
                    <div className="font-bold text-base">
                      {attemptResult.recommended_next.activity.title}
                    </div>
                    <p className="text-xs text-indigo-200 leading-relaxed">
                      {attemptResult.recommended_next.reason}
                    </p>
                    <button
                      type="button"
                      onClick={handleOpenInterventionFromAttempt}
                      className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs inline-flex items-center justify-center gap-2"
                    >
                      <span>Start Targeted Remediation &amp; Verify</span>
                      <ArrowRight className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </div>
                )}
              </div>
            )}
          </aside>
        </div>
      )}

      {/* STAGE 2: MULTIMODAL REMEDIATION STUDIO */}
      {stage === 'intervention' && activeRec && (
        <section
          aria-labelledby="remediation-heading"
          className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm hc-card space-y-6"
        >
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4">
            <div>
              <span className="inline-block text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-900 border border-emerald-300 mb-2">
                Step 2 of 3 • Multimodal Remediation Activity • {activeRec.activity.concept_name}
              </span>
              <h2
                id="remediation-heading"
                className="text-2xl font-bold text-slate-900"
              >
                {activeRec.activity.title}
              </h2>
              <p className="text-xs text-slate-600 mt-1">
                <strong>Recommendation Reason:</strong> {activeRec.reason}
              </p>
            </div>

            {/* Multimodal Presentation Selector (SRC-4) */}
            <div className="space-y-1">
              <div className="text-[11px] font-semibold text-slate-600">
                Choose Helpful Presentation Formats (Selectable preferences, not fixed learning styles):
              </div>
              <div
                className="inline-flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1 text-xs"
                role="tablist"
                aria-label="Multimodal presentation format tabs"
              >
                {[
                  { id: 'all', label: 'All Formats' },
                  { id: 'text', label: 'Text & Code' },
                  { id: 'diagram', label: 'Visual Flowchart' },
                  { id: 'audio', label: 'Audio + Transcript' },
                  { id: 'interactive', label: 'Interactive Check' },
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    role="tab"
                    aria-selected={activeFormatTab === t.id}
                    onClick={() => setActiveFormatTab(t.id as any)}
                    className={`px-3 py-1.5 rounded-lg font-semibold ${
                      activeFormatTab === t.id
                        ? 'bg-white text-indigo-900 shadow-sm'
                        : 'text-slate-700 hover:text-slate-900'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Format 1: Readable Text + Plain-Language + Annotated Code */}
          {(activeFormatTab === 'all' || activeFormatTab === 'text') && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h3 className="font-bold text-base text-slate-900 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-700" aria-hidden="true" />
                  <span>Concept Explanation</span>
                </h3>
                <p className="text-sm text-slate-800 leading-relaxed">
                  {activeRec.activity.content_body}
                </p>
                <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-950 space-y-1">
                  <div className="font-bold">Plain-Language Summary:</div>
                  <p>{activeRec.activity.plain_language_body}</p>
                </div>
              </div>

              {activeRec.activity.code_example && (
                <div className="space-y-2">
                  <h3 className="font-bold text-base text-slate-900 flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-indigo-700" aria-hidden="true" />
                    <span>Annotated Python Example</span>
                  </h3>
                  <pre className="p-4 rounded-xl bg-slate-900 text-slate-100 font-mono text-xs sm:text-sm overflow-x-auto leading-relaxed">
                    <code>{activeRec.activity.code_example}</code>
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Format 2: Visual Flowchart / SVG Diagram */}
          {(activeFormatTab === 'all' || activeFormatTab === 'diagram') &&
            activeRec.activity.diagram_svg && (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <h3 className="font-bold text-sm text-slate-900">
                  Visual Execution Diagram (Accessible SVG with text labels)
                </h3>
                <div
                  className="overflow-x-auto"
                  dangerouslySetInnerHTML={{
                    __html: activeRec.activity.diagram_svg,
                  }}
                />
              </div>
            )}

          {/* Format 3: Audio Narration + Full Transcript */}
          {(activeFormatTab === 'all' || activeFormatTab === 'audio') &&
            activeRec.activity.audio_transcript && (
              <div className="p-4 rounded-xl bg-indigo-50/60 border border-indigo-200 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-bold text-sm text-indigo-950 flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-indigo-700" aria-hidden="true" />
                    <span>Optional Audio Narration &amp; Synchronized Transcript</span>
                  </h3>
                  <button
                    type="button"
                    onClick={() =>
                      handleSpeakText(
                        activeRec.activity.audio_transcript ||
                          activeRec.activity.content_body
                      )
                    }
                    className="px-3 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-800 text-white text-xs font-semibold"
                  >
                    {isSpeaking ? 'Stop Audio Narration' : 'Play Audio Narration'}
                  </button>
                </div>
                <p className="text-xs text-slate-800 leading-relaxed">
                  <strong>Transcript / Captions:</strong>{' '}
                  {activeRec.activity.audio_transcript}
                </p>
              </div>
            )}

          {/* Format 4: Interactive Micro-Practice Check */}
          {(activeFormatTab === 'all' || activeFormatTab === 'interactive') &&
            activeRec.activity.interactive_exercise && (
              <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-300 space-y-3">
                <h3 className="font-bold text-sm text-amber-950">
                  Interactive Practice Micro-Check
                </h3>
                <p className="text-sm text-slate-900 font-medium">
                  {activeRec.activity.interactive_exercise.prompt}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <label htmlFor="micro-check-input" className="sr-only">
                    Interactive check response
                  </label>
                  <input
                    id="micro-check-input"
                    type="text"
                    value={microCheckAnswer}
                    onChange={(e) => setMicroCheckAnswer(e.target.value)}
                    placeholder="Type your quick answer..."
                    className="px-3 py-2 rounded-lg border border-slate-300 text-sm bg-white"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const expected =
                        activeRec.activity.interactive_exercise?.expected_answer ||
                        '';
                      if (
                        microCheckAnswer.trim().toLowerCase() ===
                        expected.trim().toLowerCase()
                      ) {
                        setMicroCheckFeedback(
                          `Correct! The expected value is '${expected}'. You are ready for the verification question.`
                        );
                      } else {
                        setMicroCheckFeedback(
                          `Hint: ${activeRec.activity.interactive_exercise?.hint} (Expected: ${expected})`
                        );
                      }
                    }}
                    className="px-3.5 py-2 rounded-lg bg-amber-800 text-white text-xs font-semibold"
                  >
                    Check Answer
                  </button>
                </div>
                {microCheckFeedback && (
                  <p className="text-xs font-semibold text-amber-950">
                    {microCheckFeedback}
                  </p>
                )}
              </div>
            )}

          <div className="pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setStage('question')}
              className="px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 font-semibold text-xs hover:bg-slate-50"
            >
              &larr; Back to Practice Question
            </button>
            <button
              type="button"
              onClick={handleCompleteIntervention}
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-sm shadow-sm"
            >
              <span>
                {loading
                  ? 'Loading Fresh Verification...'
                  : 'Complete Remediation & Take Fresh Verification Check'}
              </span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </section>
      )}

      {/* STAGE 3: FRESH VERIFICATION QUESTION */}
      {stage === 'verification' && verificationQuestion && (
        <section
          aria-labelledby="verification-heading"
          className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm hc-card space-y-6"
        >
          <div className="border-b border-slate-200 pb-4">
            <span className="inline-block text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-900 border border-indigo-200 mb-2">
              Step 3 of 3 • Fresh Verification Check ({verificationQuestion.stable_id})
            </span>
            <h2
              id="verification-heading"
              className="text-xl sm:text-2xl font-bold text-slate-900"
            >
              Verify Your Understanding of {verificationQuestion.concept_name}
            </h2>
            <p className="text-xs text-slate-600 mt-1">
              This is a fresh question testing the same underlying concept to check whether the targeted remediation helped resolve the error pattern.
            </p>
          </div>

          <div className="space-y-4">
            <p className="text-base font-bold text-slate-900">
              {verificationQuestion.content}
            </p>
            {verificationQuestion.code_snippet && (
              <pre className="p-4 rounded-xl bg-slate-900 text-slate-100 font-mono text-sm overflow-x-auto">
                <code>{verificationQuestion.code_snippet}</code>
              </pre>
            )}

            <form onSubmit={handleSubmitVerification} className="space-y-3">
              {verificationQuestion.options.map((opt) => (
                <label
                  key={opt.id}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer ${
                    verificationChoice === opt.option_key
                      ? 'bg-indigo-50 border-indigo-600 font-semibold'
                      : 'bg-white border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="radio"
                    name="verification-option"
                    value={opt.option_key}
                    checked={verificationChoice === opt.option_key}
                    onChange={() => setVerificationChoice(opt.option_key)}
                    className="mt-1 h-4 w-4"
                  />
                  <span className="text-sm">
                    <strong className="font-mono mr-2">{opt.option_key}.</strong>
                    {opt.option_text}
                  </span>
                </label>
              ))}

              {!verificationResult && (
                <button
                  type="submit"
                  disabled={!verificationChoice || loading}
                  className="px-5 py-2.5 rounded-xl bg-indigo-700 hover:bg-indigo-800 disabled:opacity-50 text-white font-semibold text-sm"
                >
                  {loading ? 'Verifying...' : 'Submit Verification Answer'}
                </button>
              )}
            </form>
          </div>

          {verificationResult && (
            <div
              role="status"
              aria-live="polite"
              className={`p-5 rounded-2xl border space-y-3 ${
                verificationResult.is_correct
                  ? 'bg-emerald-50 border-emerald-400 text-emerald-950'
                  : 'bg-amber-50 border-amber-400 text-slate-900'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-bold text-base flex items-center gap-2">
                  {verificationResult.is_correct ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-700" aria-hidden="true" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-700" aria-hidden="true" />
                  )}
                  <span>
                    Immediate Verification Result:{' '}
                    {verificationResult.is_correct
                      ? 'Concept Gap Resolved on Immediate Follow-Up!'
                      : 'Needs Further Practice'}
                  </span>
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-white border border-slate-300">
                  Original Error Recurred: {verificationResult.error_recurred ? 'Yes' : 'No'}
                </span>
              </div>

              <p className="text-sm leading-relaxed">
                {verificationResult.explanation}
              </p>

              <div className="p-3 rounded-xl bg-white border border-slate-200 text-xs flex flex-wrap items-center justify-between gap-2">
                <span>
                  <strong>Updated {verificationResult.mastery_update.concept_name} Mastery Estimate:</strong>{' '}
                  {Math.round(verificationResult.mastery_update.pre_mastery * 100)}% &rarr;{' '}
                  {Math.round(verificationResult.mastery_update.post_mastery * 100)}% (
                  {verificationResult.mastery_update.status_label})
                </span>
                <span className="text-slate-600 italic">
                  {verificationResult.retention_disclaimer}
                </span>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => loadQuestion(null, verificationQuestion.id)}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-700 hover:bg-indigo-800 text-white font-semibold text-xs"
                >
                  <span>Continue to Next Adaptive Question</span>
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
};
