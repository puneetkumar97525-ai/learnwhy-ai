import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock,
  Compass,
  GitBranch,
  HelpCircle,
  Layers,
  Lock,
  Play,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react';
import { api } from '../services/api';
import {
  ConceptNode,
  RecommendationItem,
  UserProfile,
} from '../types/api';

interface HomeViewProps {
  user: UserProfile;
  onStartPractice: (conceptId?: number | null) => void;
  onStartRecommendation: (rec: RecommendationItem) => void;
}

export const HomeView: React.FC<HomeViewProps> = ({
  user,
  onStartPractice,
  onStartRecommendation,
}) => {
  const [concepts, setConcepts] = useState<ConceptNode[]>([]);
  const [modelDisclaimer, setModelDisclaimer] = useState<string>('');
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [strategy, setStrategy] = useState<'proposed' | 'baseline_score'>('proposed');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (selectedStrategy: 'proposed' | 'baseline_score') => {
    setLoading(true);
    setError(null);
    try {
      const courseId = user.selected_course_id || 1;
      const [conceptRes, recRes] = await Promise.all([
        api.getCourseConcepts(courseId),
        api.getRecommendations(selectedStrategy, true),
      ]);
      setConcepts(conceptRes.concepts || []);
      setModelDisclaimer(conceptRes.model_disclaimer || '');
      setRecommendations(recRes.recommendations || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load course and recommendation data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(strategy);
  }, [strategy]);

  const conceptMapById = React.useMemo(() => {
    const map: Record<number, ConceptNode> = {};
    concepts.forEach((c) => {
      map[c.id] = c;
    });
    return map;
  }, [concepts]);

  const topRec = recommendations[0] || null;

  const getMasteryBadgeStyle = (mastery: number, attempts: number) => {
    if (attempts === 0) {
      return 'bg-slate-100 text-slate-800 border-slate-300';
    }
    if (mastery >= 0.75) {
      return 'bg-emerald-50 text-emerald-900 border-emerald-300';
    }
    if (mastery >= 0.5) {
      return 'bg-amber-50 text-amber-900 border-amber-300';
    }
    return 'bg-rose-50 text-rose-900 border-rose-300';
  };

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="p-8 bg-white rounded-2xl border border-slate-200 shadow-sm text-center space-y-3"
      >
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm font-medium text-slate-700">
          Loading your personalized Python concept map and recommendations...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="p-6 bg-rose-50 rounded-2xl border border-rose-300 text-rose-900 space-y-3"
      >
        <p className="font-semibold">{error}</p>
        <button
          type="button"
          onClick={() => loadData(strategy)}
          className="px-4 py-2 rounded-xl bg-rose-700 text-white text-sm font-semibold"
        >
          Retry Loading
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Hero Banner + Top Explainable Recommendation */}
      <section
        aria-labelledby="home-welcome-heading"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6"
      >
        {/* Welcome & Quick Action */}
        <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card flex flex-col justify-between space-y-5">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-md border border-indigo-200">
              <Compass className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Personalized Learning Path</span>
            </div>
            <h1
              id="home-welcome-heading"
              className="text-2xl font-bold text-slate-900 tracking-tight"
            >
              Welcome back, {user.full_name.split(' ')[0]}
            </h1>
            <p className="text-sm text-slate-700 leading-relaxed">
              Your learning path adapts to each concept attempt. Answer a diagnostic question, inspect why an answer works or fails, and verify your understanding with a fresh check.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>Daily Learning Goal ({user.daily_goal_minutes} mins)</span>
              <span className="text-indigo-700 font-bold">{user.points} Points Earned</span>
            </div>
            <div
              className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={Math.min(100, Math.round((user.points / 150) * 100))}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Progress toward milestone"
            >
              <div
                className="h-full bg-indigo-600 rounded-full"
                style={{ width: `${Math.min(100, Math.max(15, Math.round((user.points / 150) * 100)))}%` }}
              />
            </div>
            <p className="text-xs text-slate-600">
              Effort is always rewarded. Using hints, audio transcripts, or plain-language explanations never reduces your score.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => onStartPractice(null)}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-indigo-700 hover:bg-indigo-800 text-white font-semibold text-sm shadow-sm transition-colors"
            >
              <Play className="w-4 h-4" aria-hidden="true" />
              <span>Start Adaptive Question</span>
            </button>
          </div>
        </div>

        {/* Top Explainable Recommendation Card */}
        <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card flex flex-col justify-between space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-700" aria-hidden="true" />
              <h2 className="text-lg font-bold text-slate-900">
                Next Recommended Activity & Why
              </h2>
            </div>

            {/* Strategy comparison toggle (Proposed B vs Baseline A) */}
            <div
              className="inline-flex items-center rounded-lg bg-slate-100 p-1 text-xs"
              role="group"
              aria-label="Recommendation algorithm selector"
            >
              <button
                type="button"
                onClick={() => setStrategy('proposed')}
                aria-pressed={strategy === 'proposed'}
                className={`px-2.5 py-1 rounded-md font-semibold transition-colors ${
                  strategy === 'proposed'
                    ? 'bg-white text-indigo-800 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Proposed B (Explainable)
              </button>
              <button
                type="button"
                onClick={() => setStrategy('baseline_score')}
                aria-pressed={strategy === 'baseline_score'}
                className={`px-2.5 py-1 rounded-md font-semibold transition-colors ${
                  strategy === 'baseline_score'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Baseline A (Score-Only)
              </button>
            </div>
          </div>

          {topRec ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-md bg-amber-50 text-amber-900 border border-amber-300 mb-1.5">
                    Target Concept: {topRec.activity.concept_name} • Level {topRec.activity.difficulty}
                  </span>
                  <h3 className="text-xl font-bold text-slate-900">
                    {topRec.activity.title}
                  </h3>
                </div>
                <div className="text-right bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-xl">
                  <div className="text-[11px] uppercase tracking-wider font-semibold text-indigo-800">
                    Rank #1 Score
                  </div>
                  <div className="text-lg font-bold text-indigo-950 font-mono">
                    R = {topRec.total_score.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* Human-readable explanation of recommendation */}
              <div className="p-3.5 rounded-xl bg-indigo-50/70 border border-indigo-200 text-sm text-slate-800">
                <span className="font-bold text-indigo-950">Why this was selected: </span>
                {topRec.reason}
              </div>

              {/* Transparent Score Components Breakdown */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="font-semibold text-slate-600">
                    Gap Relevance (w = {topRec.score_components.weights.gap_relevance.toFixed(2)})
                  </div>
                  <div className="text-base font-bold text-slate-900 font-mono mt-0.5">
                    {topRec.score_components.gap_relevance.toFixed(2)} / 1.00
                  </div>
                  <div className="text-[11px] text-slate-600 mt-0.5">
                    {topRec.score_components.targets_diagnosed_misconception
                      ? 'Directly targets diagnosed misconception'
                      : 'Addresses concept mastery gap'}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="font-semibold text-slate-600">
                    Prerequisite Weight (w = {topRec.score_components.weights.prerequisite_importance.toFixed(2)})
                  </div>
                  <div className="text-base font-bold text-slate-900 font-mono mt-0.5">
                    {topRec.score_components.prerequisite_importance.toFixed(2)} / 1.00
                  </div>
                  <div className="text-[11px] text-slate-600 mt-0.5">
                    Downstream curriculum dependency
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="font-semibold text-slate-600">
                    Difficulty & Format Fit (w = {topRec.score_components.weights.difficulty_fit.toFixed(2)})
                  </div>
                  <div className="text-base font-bold text-slate-900 font-mono mt-0.5">
                    {topRec.score_components.difficulty_fit.toFixed(2)} / 1.00
                  </div>
                  <div className="text-[11px] text-slate-600 mt-0.5">
                    Format: {topRec.activity.format} (~{topRec.activity.estimated_duration} min)
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <span className="text-xs text-slate-600 font-mono">
                  Rule version: {topRec.rule_version} (Provisional configurable weights)
                </span>
                <button
                  type="button"
                  onClick={() => onStartRecommendation(topRec)}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-sm shadow-sm transition-colors"
                >
                  <span>Open Remediation & Verify</span>
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-600">
              No pending recommendations right now. Complete a practice question to generate personalized recommendations.
            </p>
          )}
        </div>
      </section>

      {/* Python Concept Graph & Prerequisite Map */}
      <section
        aria-labelledby="concept-map-heading"
        className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-indigo-700" aria-hidden="true" />
              <h2 id="concept-map-heading" className="text-xl font-bold text-slate-900">
                Python Concept Map & Prerequisite Graph
              </h2>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {modelDisclaimer}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-900 border border-emerald-300 font-semibold">
              Strong evidence (&ge;75%)
            </span>
            <span className="px-2.5 py-1 rounded-md bg-amber-50 text-amber-900 border border-amber-300 font-semibold">
              Developing (50–74%)
            </span>
            <span className="px-2.5 py-1 rounded-md bg-rose-50 text-rose-900 border border-rose-300 font-semibold">
              Needs practice (&lt;50%)
            </span>
          </div>
        </div>

        {/* Accessible Visual DAG Flow Summary */}
        <div
          className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700"
          role="region"
          aria-label="Prerequisite dependency chains"
        >
          <div className="font-semibold text-slate-900 mb-1.5">
            Curriculum Prerequisite Chains (Directed Acyclic Graph):
          </div>
          <div className="flex flex-wrap items-center gap-2 font-mono">
            <span className="px-2 py-1 rounded bg-white border border-slate-300">
              1. Variables & Expressions
            </span>
            <span>&rarr;</span>
            <span className="px-2 py-1 rounded bg-white border border-slate-300">
              2. Conditions & Branching
            </span>
            <span>&rarr;</span>
            <span className="px-2 py-1 rounded bg-white border border-slate-300">
              3. Loops & Stopping Conditions
            </span>
            <span>&rarr;</span>
            <span className="px-2 py-1 rounded bg-white border border-slate-300">
              4. Functions, Parameters & Return
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 font-mono mt-2">
            <span className="px-2 py-1 rounded bg-white border border-slate-300">
              1. Variables & Expressions
            </span>
            <span>&rarr;</span>
            <span className="px-2 py-1 rounded bg-white border border-slate-300">
              5. Lists & Indexing
            </span>
            <span>+ 3. Loops &rarr;</span>
            <span className="px-2 py-1 rounded bg-white border border-slate-300">
              6. List Iteration & Filtering
            </span>
          </div>
        </div>

        {/* Concept Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {concepts.map((concept) => {
            const prereqNames = concept.prerequisite_ids
              .map((pid) => conceptMapById[pid]?.name)
              .filter(Boolean);

            return (
              <article
                key={concept.id}
                aria-label={`Concept ${concept.order_index}: ${concept.name}`}
                className="rounded-2xl border border-slate-200 bg-white p-5 flex flex-col justify-between space-y-4 hover:border-indigo-300 transition-colors hc-card"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md">
                      Module {concept.order_index}
                    </span>
                    <span
                      className={`text-xs font-semibold px-2.5 py-1 rounded-md border ${getMasteryBadgeStyle(
                        concept.mastery,
                        concept.attempts_count
                      )}`}
                    >
                      {concept.status_label}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-lg font-bold text-slate-900">
                      {concept.name}
                    </h3>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {concept.description}
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-700">
                        Mastery Estimate:
                      </span>
                      <span className="font-bold font-mono text-slate-900">
                        {concept.mastery_percent}% (&plusmn;{Math.round(concept.uncertainty * 100)}%)
                      </span>
                    </div>
                    <div
                      className="w-full h-2 bg-slate-200 rounded-full overflow-hidden"
                      role="progressbar"
                      aria-valuenow={concept.mastery_percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${concept.name} mastery estimate ${concept.mastery_percent}%`}
                    >
                      <div
                        className={`h-full rounded-full ${
                          concept.mastery >= 0.75
                            ? 'bg-emerald-600'
                            : concept.mastery >= 0.5
                            ? 'bg-amber-500'
                            : 'bg-indigo-600'
                        }`}
                        style={{ width: `${Math.max(8, concept.mastery_percent)}%` }}
                      />
                    </div>
                    <div className="text-[11px] text-slate-600">
                      Observed evidence: {concept.attempts_count} attempt(s), {concept.correct_count} correct
                    </div>
                  </div>

                  <div className="text-xs text-slate-700 space-y-1">
                    <div>
                      <span className="font-semibold">Objective: </span>
                      {concept.learning_objective}
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-600">
                      {concept.prerequisites_ready ? (
                        <CheckCircle2
                          className="w-3.5 h-3.5 text-emerald-700 shrink-0"
                          aria-hidden="true"
                        />
                      ) : (
                        <Lock
                          className="w-3.5 h-3.5 text-amber-700 shrink-0"
                          aria-hidden="true"
                        />
                      )}
                      <span>
                        Prerequisites:{' '}
                        {prereqNames.length > 0 ? prereqNames.join(', ') : 'None (Entry concept)'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => onStartPractice(concept.id)}
                    className="w-full inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-900 font-semibold text-xs border border-indigo-200 transition-colors"
                  >
                    <Target className="w-3.5 h-3.5 text-indigo-700" aria-hidden="true" />
                    <span>Practice {concept.name}</span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
};
