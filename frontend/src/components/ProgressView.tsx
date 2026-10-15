import React, { useEffect, useState } from 'react';
import {
  Award,
  BarChart3,
  CheckCircle2,
  Flame,
  History,
  ShieldAlert,
  Table,
  TrendingUp,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../services/api';

export const ProgressView: React.FC = () => {
  const [summary, setSummary] = useState<any | null>(null);
  const [showTableView, setShowTableView] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProgress = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProgressSummary();
      setSummary(data);
    } catch (err: any) {
      setError(err?.message || 'Unable to load progress summary.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProgress();
  }, []);

  if (loading) {
    return (
      <div
        role="status"
        className="p-8 bg-white rounded-2xl border border-slate-200 text-center text-sm text-slate-600"
      >
        Loading concept mastery estimates, milestones, and intervention history...
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div
        role="alert"
        className="p-6 bg-rose-50 rounded-2xl border border-rose-300 text-rose-900"
      >
        {error || 'No progress summary available.'}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top KPI Summary Cards */}
      <section
        aria-label="Learner progress highlights"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Course Mastery Estimate
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">
            {summary.overall_mastery_percent}%
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Heuristic EMA average across 6 Python concepts
          </p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Practice Attempts
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">
            {summary.total_attempts}
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Recorded with deterministic answer validation
          </p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Verified Remediations
          </div>
          <div className="text-2xl font-bold text-emerald-800 mt-1 font-mono">
            {summary.verified_interventions_count}
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Completed with a fresh verification question
          </p>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Supportive Engagement
          </div>
          <div className="text-2xl font-bold text-amber-800 mt-1 font-mono">
            {summary.gamification.points} pts
          </div>
          <p className="text-xs text-slate-600 mt-1">
            {summary.gamification.streak_opt_in
              ? `${summary.gamification.current_streak}-day active pace`
              : 'Optional streak paused by preference'}
          </p>
        </div>
      </section>

      {/* Concept Mastery Chart + Accessible Table Alternative */}
      <section
        aria-labelledby="progress-chart-heading"
        className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <h2
              id="progress-chart-heading"
              className="text-xl font-bold text-slate-900 flex items-center gap-2"
            >
              <BarChart3 className="w-5 h-5 text-indigo-700" aria-hidden="true" />
              <span>Concept-Level Mastery Estimates &amp; Evidence</span>
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Estimates are in [0, 100%] with uncertainty bounds. Toggle the accessible data table anytime.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setShowTableView((prev) => !prev)}
            aria-pressed={showTableView}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-800"
          >
            <Table className="w-4 h-4 text-indigo-700" aria-hidden="true" />
            <span>
              {showTableView
                ? 'Show Both Chart & Table'
                : 'Highlight Accessible Data Table'}
            </span>
          </button>
        </div>

        {/* Visual BarChart */}
        <div
          className="h-64 w-full"
          role="img"
          aria-label="Bar chart of concept mastery estimates across the 6 Python concepts"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={summary.concepts}
              margin={{ top: 10, right: 20, left: 0, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar
                dataKey="mastery_percent"
                name="Mastery Estimate (%)"
                fill="#4338ca"
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Always-present Accessible HTML Data Table Alternative */}
        <div className="overflow-x-auto">
          <table
            aria-label="Concept mastery estimates and supporting evidence table"
            className="w-full text-left border-collapse text-xs sm:text-sm"
          >
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-700">
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Concept
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Mastery Estimate
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Attempts (Correct)
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Status Label (Non-Color Cue)
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Supporting Evidence
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {summary.concepts.map((c: any) => (
                <tr key={c.concept_id} className="hover:bg-slate-50">
                  <th scope="row" className="py-2.5 px-3 font-semibold text-slate-900">
                    {c.name}
                  </th>
                  <td className="py-2.5 px-3 font-mono font-bold text-indigo-900">
                    {c.mastery_percent}% (&plusmn;{Math.round(c.uncertainty * 100)}%)
                  </td>
                  <td className="py-2.5 px-3 font-mono">
                    {c.attempts_count} ({c.correct_count} correct)
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-300 text-xs font-semibold text-slate-800">
                      {c.status_label}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-xs text-slate-600">
                    {c.evidence_note}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Gamification Milestones & Earning Rules */}
      <section
        aria-labelledby="milestones-heading"
        className="grid grid-cols-1 lg:grid-cols-12 gap-6"
      >
        <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-600" aria-hidden="true" />
            <h2 id="milestones-heading" className="text-lg font-bold text-slate-900">
              Milestones &amp; Badges (Supportive Gamification)
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {summary.gamification.achievements.map((ach: any) => (
              <div
                key={ach.id}
                className={`p-4 rounded-xl border ${
                  ach.earned
                    ? 'bg-amber-50/70 border-amber-400 text-slate-900'
                    : 'bg-slate-50 border-slate-200 text-slate-600'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-sm">{ach.name}</span>
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-white border border-slate-300">
                    {ach.earned ? 'EARNED' : 'LOCKED'} (+{ach.points_reward} pts)
                  </span>
                </div>
                <p className="text-xs mt-1 leading-relaxed">{ach.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <h3 className="text-lg font-bold text-slate-900">
            Transparent Point Earning Rules
          </h3>
          <p className="text-xs text-slate-600">
            Core learning content is never locked behind points or streaks. Accessibility features and hints never penalize points.
          </p>
          <ul className="divide-y divide-slate-200 text-xs">
            {summary.gamification.earning_rules.map((r: any, idx: number) => (
              <li
                key={idx}
                className="py-2.5 flex items-center justify-between gap-2"
              >
                <span className="font-medium text-slate-800">{r.action}</span>
                <span className="font-mono font-bold text-indigo-800">
                  {r.points}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Intervention & Diagnosis History */}
      <section
        aria-label="Diagnosis and intervention history"
        className="grid grid-cols-1 lg:grid-cols-2 gap-6"
      >
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-indigo-700" aria-hidden="true" />
            <span>Recent Misconception Diagnoses</span>
          </h3>
          {summary.recent_diagnoses.length === 0 ? (
            <p className="text-xs text-slate-600">No diagnoses recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {summary.recent_diagnoses.map((d: any) => (
                <div
                  key={d.id}
                  className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between font-semibold text-slate-900">
                    <span>{d.concept_name}</span>
                    <span className="px-2 py-0.5 rounded bg-white border border-slate-300 font-mono">
                      {d.status} ({Math.round(d.confidence * 100)}%)
                    </span>
                  </div>
                  {d.misconception_label && (
                    <div className="text-indigo-900 font-semibold">
                      Candidate: {d.misconception_label}
                    </div>
                  )}
                  <p className="text-slate-600">{d.evidence}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-700" aria-hidden="true" />
            <span>Remediation &amp; Verification Outcomes</span>
          </h3>
          {summary.intervention_history.length === 0 ? (
            <p className="text-xs text-slate-600">
              No verified interventions yet. Complete a recommended activity to see pre/post verification results.
            </p>
          ) : (
            <div className="space-y-3">
              {summary.intervention_history.map((o: any) => (
                <div
                  key={o.id}
                  className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between font-semibold text-slate-900">
                    <span>{o.concept_name}</span>
                    <span className="px-2 py-0.5 rounded bg-emerald-50 border border-emerald-300 text-emerald-900">
                      Immediate Outcome: {o.immediate_outcome}
                    </span>
                  </div>
                  <div className="font-mono text-slate-700">
                    Mastery: {Math.round(o.pre_mastery * 100)}% &rarr;{' '}
                    {Math.round(o.post_mastery * 100)}% | Error Recurred:{' '}
                    {o.error_recurred ? 'Yes' : 'No'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
