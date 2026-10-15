import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  BarChart2,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Filter,
  FlaskConical,
  GraduationCap,
  MessageSquarePlus,
  Users,
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

export const EducatorInsightsView: React.FC = () => {
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [evalReport, setEvalReport] = useState<any | null>(null);
  const [conceptFilter, setConceptFilter] = useState<number | null>(null);
  const [noteInputs, setNoteInputs] = useState<Record<number, string>>({});
  const [noteStatus, setNoteStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (cId: number | null) => {
    setLoading(true);
    setError(null);
    try {
      const [anaRes, evalRes] = await Promise.all([
        api.getEducatorAnalytics(1, cId),
        api.getEvaluationReport(),
      ]);
      setAnalytics(anaRes);
      setEvalReport(evalRes);
    } catch (err: any) {
      setError(err?.message || 'Unable to load educator analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(conceptFilter);
  }, [conceptFilter]);

  const handleDownloadCsv = async () => {
    try {
      const csvText = await api.downloadEducatorCsv(1);
      const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'learnwhy_class_1_aggregate_report.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err?.message || 'CSV export failed.');
    }
  };

  const handleSaveEducatorNote = async (outcomeId: number) => {
    const text = noteInputs[outcomeId];
    if (!text || text.trim().length < 2) return;
    try {
      await api.acknowledgeEducatorAlert(1, outcomeId, text);
      setNoteStatus(`Saved educator review note for Outcome #${outcomeId}.`);
      loadData(conceptFilter);
    } catch (err: any) {
      setError(err?.message || 'Could not save educator note.');
    }
  };

  if (loading) {
    return (
      <div
        role="status"
        className="p-8 bg-white rounded-2xl border border-slate-200 text-center text-sm text-slate-600"
      >
        Loading authorized educator analytics and research evaluation metrics...
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div
        role="alert"
        className="p-6 bg-rose-50 rounded-2xl border border-rose-300 text-rose-900"
      >
        {error || 'No educator analytics available.'}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header & Aggregate CSV Export */}
      <section
        aria-labelledby="educator-heading"
        className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card flex flex-wrap items-center justify-between gap-4"
      >
        <div>
          <span className="inline-block text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-900 border border-indigo-200 mb-1.5">
            Authorized Educator &amp; Researcher Dashboard (SRC-6)
          </span>
          <h1 id="educator-heading" className="text-2xl font-bold text-slate-900">
            {analytics.class_name}
          </h1>
          <p className="text-xs text-slate-600 mt-1 max-w-3xl">
            {analytics.alert_methodology_note}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label
              htmlFor="educator-concept-filter"
              className="text-xs font-semibold text-slate-700"
            >
              Filter Concept:
            </label>
            <select
              id="educator-concept-filter"
              value={conceptFilter || ''}
              onChange={(e) =>
                setConceptFilter(e.target.value ? Number(e.target.value) : null)
              }
              className="px-3 py-2 rounded-xl border border-slate-300 text-xs font-medium bg-white"
            >
              <option value="">All Python Concepts</option>
              <option value="1">1. Variables &amp; Expressions</option>
              <option value="2">2. Conditions &amp; Branching</option>
              <option value="3">3. Loops &amp; Stopping Conditions</option>
              <option value="4">4. Functions, Parameters &amp; Return</option>
              <option value="5">5. Lists, Indexing &amp; Mutability</option>
              <option value="6">6. List Iteration &amp; Filtering</option>
            </select>
          </div>

          <button
            type="button"
            onClick={handleDownloadCsv}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-700 hover:bg-indigo-800 text-white font-semibold text-xs shadow-sm"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            <span>Export Aggregate CSV Report</span>
          </button>
        </div>
      </section>

      {/* Class Summary KPI Cards */}
      <section
        aria-label="Class summary metrics"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
      >
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-semibold text-slate-600">Active Learners</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {analytics.summary.active_students}
          </div>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-semibold text-slate-600">Total Attempts</div>
          <div className="text-2xl font-bold text-slate-900 font-mono mt-1">
            {analytics.summary.total_attempts}
          </div>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-semibold text-slate-600">Overall Accuracy</div>
          <div className="text-2xl font-bold text-indigo-800 font-mono mt-1">
            {analytics.summary.overall_accuracy_percent}%
          </div>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-semibold text-slate-600">
            Immediate Verification Accuracy
          </div>
          <div className="text-2xl font-bold text-emerald-800 font-mono mt-1">
            {analytics.summary.immediate_verification_accuracy_percent}%
          </div>
        </div>
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hc-card">
          <div className="text-xs font-semibold text-slate-600">
            Error Recurrence Rate
          </div>
          <div className="text-2xl font-bold text-amber-800 font-mono mt-1">
            {analytics.summary.error_recurrence_rate_percent}%
          </div>
        </div>
      </section>

      {/* Concept Performance Chart + Accessible Data Table */}
      <section
        aria-labelledby="class-concept-heading"
        className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-5"
      >
        <h2
          id="class-concept-heading"
          className="text-lg font-bold text-slate-900 flex items-center gap-2"
        >
          <BarChart2 className="w-5 h-5 text-indigo-700" aria-hidden="true" />
          <span>Class-Level Concept Performance &amp; Accessible Breakdown</span>
        </h2>

        <div
          className="h-60 w-full"
          role="img"
          aria-label="Bar chart of class average mastery and accuracy by concept"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={analytics.concept_performance}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="concept_name" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar
                dataKey="average_mastery_percent"
                name="Avg Mastery Estimate (%)"
                fill="#4338ca"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="accuracy_percent"
                name="Attempt Accuracy (%)"
                fill="#0d9488"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="overflow-x-auto">
          <table
            aria-label="Class concept performance table"
            className="w-full text-left border-collapse text-xs sm:text-sm"
          >
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-700">
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Concept
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Avg Mastery Estimate
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Total Attempts
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Accuracy
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Learners Flagged for Review
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {analytics.concept_performance.map((cp: any) => (
                <tr key={cp.concept_id}>
                  <th scope="row" className="py-2.5 px-3 font-semibold text-slate-900">
                    {cp.concept_name}
                  </th>
                  <td className="py-2.5 px-3 font-mono font-bold text-indigo-900">
                    {cp.average_mastery_percent}%
                  </td>
                  <td className="py-2.5 px-3 font-mono">{cp.total_attempts}</td>
                  <td className="py-2.5 px-3 font-mono">{cp.accuracy_percent}%</td>
                  <td className="py-2.5 px-3 font-mono font-semibold text-amber-900">
                    {cp.students_needing_review} learner(s)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Common Misconceptions & Learners Flagged for Supportive Review */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-6 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <h2 className="text-lg font-bold text-slate-900">
            Common Misconceptions &amp; Error Patterns
          </h2>
          {analytics.common_misconceptions.length === 0 ? (
            <p className="text-xs text-slate-600">
              No misconception patterns recorded for this filter.
            </p>
          ) : (
            <div className="space-y-3">
              {analytics.common_misconceptions.map((cm: any) => (
                <div
                  key={cm.misconception_id}
                  className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-bold text-indigo-900">
                      [{cm.code}] • {cm.concept_name}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-amber-50 border border-amber-300 font-bold text-amber-900">
                      {cm.occurrences} occurrence(s) • Avg Conf{' '}
                      {Math.round(cm.average_confidence * 100)}%
                    </span>
                  </div>
                  <div className="font-bold text-sm text-slate-900">
                    {cm.label}
                  </div>
                  <p className="text-slate-600">
                    <strong>Remediation Focus:</strong> {cm.remediation_focus}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-6 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <h2 className="text-lg font-bold text-slate-900">
            Learners Flagged for Supportive Review
          </h2>
          <p className="text-xs text-slate-600">
            Explainable alert rule:{' '}
            <code className="bg-slate-100 px-1.5 py-0.5 rounded">
              (attempts &gt;= 2 AND mastery &lt; 0.48) OR (misconception_flags &gt;= 2)
            </code>
          </p>
          {analytics.learners_flagged_for_review.length === 0 ? (
            <p className="text-xs text-slate-600">
              No learners currently meet the supportive review alert threshold.
            </p>
          ) : (
            <div className="space-y-3">
              {analytics.learners_flagged_for_review.map((lr: any, idx: number) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-rose-50/60 border border-rose-300 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between gap-2 font-bold text-slate-900 text-sm">
                    <span>{lr.student_name}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-white border border-rose-300 text-rose-900">
                      {lr.concept_name}: {lr.mastery_percent}% ({lr.attempts_count} attempts)
                    </span>
                  </div>
                  <div className="text-slate-800">
                    <strong>Candidate Misconception:</strong>{' '}
                    {lr.candidate_misconception}
                  </div>
                  <div className="text-slate-600">
                    <strong>Why Flagged:</strong> {lr.alert_reason}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Intervention Outcomes & Educator Review Note / Override */}
      <section className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-bold text-slate-900">
            Post-Intervention Verification Outcomes &amp; Educator Notes
          </h2>
          {noteStatus && (
            <span className="text-xs font-semibold text-emerald-800 bg-emerald-50 px-3 py-1 rounded-lg border border-emerald-300">
              {noteStatus}
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table
            aria-label="Intervention outcomes and educator review notes"
            className="w-full text-left border-collapse text-xs"
          >
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-700">
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Learner
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Concept &amp; Misconception
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Pre &rarr; Post Mastery
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Immediate Outcome
                </th>
                <th scope="col" className="py-2.5 px-3 font-semibold">
                  Educator Review Note / Override
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {analytics.intervention_outcomes.map((o: any) => (
                <tr key={o.id}>
                  <td className="py-3 px-3 font-semibold text-slate-900">
                    {o.student_name}
                  </td>
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-900">
                      {o.concept_name}
                    </div>
                    {o.original_misconception && (
                      <div className="text-slate-600">
                        Target: {o.original_misconception}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-3 font-mono">
                    {Math.round(o.pre_mastery * 100)}% &rarr;{' '}
                    {Math.round(o.post_mastery * 100)}%
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-50 border border-emerald-300 font-semibold text-emerald-900">
                      {o.immediate_outcome} (Recurred: {o.error_recurred ? 'Yes' : 'No'})
                    </span>
                  </td>
                  <td className="py-3 px-3 space-y-1.5">
                    {o.educator_note && (
                      <div className="text-slate-700 bg-slate-50 p-2 rounded border border-slate-200">
                        {o.educator_note}
                      </div>
                    )}
                    <div className="flex items-center gap-1.5">
                      <label htmlFor={`edu-note-${o.id}`} className="sr-only">
                        Add educator note for outcome {o.id}
                      </label>
                      <input
                        id={`edu-note-${o.id}`}
                        type="text"
                        placeholder="Add educator review note..."
                        value={noteInputs[o.id] || ''}
                        onChange={(e) =>
                          setNoteInputs((prev) => ({
                            ...prev,
                            [o.id]: e.target.value,
                          }))
                        }
                        className="px-2.5 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"
                      />
                      <button
                        type="button"
                        onClick={() => handleSaveEducatorNote(o.id)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-white font-semibold text-xs"
                      >
                        Save Note
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Reproducible Evaluation & Baseline Comparison Section (PRD Section 13) */}
      {evalReport && evalReport.comparison_summary && (
        <section
          aria-labelledby="research-eval-heading"
          className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-5"
        >
          <div className="border-b border-slate-200 pb-4 space-y-1.5">
            <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-amber-50 text-amber-900 border border-amber-300">
              <FlaskConical className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Reproducible Evaluation Benchmark (Synthetic / Expert-Labeled)</span>
            </div>
            <h2
              id="research-eval-heading"
              className="text-xl font-bold text-slate-900"
            >
              {evalReport.evaluation_title}
            </h2>
            <p className="text-xs text-slate-700 leading-relaxed bg-amber-50/70 p-3 rounded-xl border border-amber-200">
              {evalReport.methodology_and_limitations}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="font-bold text-slate-900">
                Held-Out Diagnosis Precision / Recall / F1
              </div>
              <div className="text-lg font-bold font-mono text-indigo-900">
                P: {(evalReport.diagnosis_metrics_held_out_test.macro_precision * 100).toFixed(1)}% | R:{' '}
                {(evalReport.diagnosis_metrics_held_out_test.macro_recall * 100).toFixed(1)}% | F1:{' '}
                {(evalReport.diagnosis_metrics_held_out_test.macro_f1 * 100).toFixed(1)}%
              </div>
              <div className="text-slate-600">
                Split: N_dev = {evalReport.sample_sizes.development_split_n}, N_test ={' '}
                {evalReport.sample_sizes.held_out_test_split_n} (No test-split tuning)
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="font-bold text-slate-900">
                Top-1 Recommendation Relevance Rate
              </div>
              <div className="text-lg font-bold font-mono text-emerald-900">
                Proposed B:{' '}
                {(
                  evalReport.comparison_summary.proposed_b_misconception_aware
                    .recommendation_relevance_rate * 100
                ).toFixed(1)}
                % vs Baseline A:{' '}
                {(
                  evalReport.comparison_summary.baseline_a_score_based
                    .recommendation_relevance_rate * 100
                ).toFixed(1)}
                %
              </div>
              <div className="text-slate-600">
                Matches expert-assigned remediation activity for diagnosed gap
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="font-bold text-slate-900">
                API Latency &amp; Reliability (N = {evalReport.system_performance.total_api_requests} calls)
              </div>
              <div className="text-lg font-bold font-mono text-slate-900">
                p50: {evalReport.system_performance.latency_p50_ms} ms | p95:{' '}
                {evalReport.system_performance.latency_p95_ms} ms
              </div>
              <div className="text-slate-600">
                Error Rate: {evalReport.system_performance.api_error_rate * 100}% (&lt;500 ms p95 target met)
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table
              aria-label="Baseline A versus Proposed B comparison table"
              className="w-full text-left border-collapse text-xs"
            >
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-700">
                  <th scope="col" className="py-2.5 px-3 font-semibold">
                    Method
                  </th>
                  <th scope="col" className="py-2.5 px-3 font-semibold">
                    Recommendation Relevance
                  </th>
                  <th scope="col" className="py-2.5 px-3 font-semibold">
                    Simulated Immediate Verification Accuracy
                  </th>
                  <th scope="col" className="py-2.5 px-3 font-semibold">
                    Simulated Error Recurrence Rate
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                <tr>
                  <th scope="row" className="py-2.5 px-3 font-semibold text-slate-800">
                    {evalReport.comparison_summary.baseline_a_score_based.method}
                  </th>
                  <td className="py-2.5 px-3 font-mono">
                    {(
                      evalReport.comparison_summary.baseline_a_score_based
                        .recommendation_relevance_rate * 100
                    ).toFixed(1)}
                    %
                  </td>
                  <td className="py-2.5 px-3 font-mono">
                    {(
                      evalReport.comparison_summary.baseline_a_score_based
                        .simulated_immediate_verification_accuracy * 100
                    ).toFixed(1)}
                    %
                  </td>
                  <td className="py-2.5 px-3 font-mono">
                    {(
                      evalReport.comparison_summary.baseline_a_score_based
                        .simulated_error_recurrence_rate * 100
                    ).toFixed(1)}
                    %
                  </td>
                </tr>
                <tr className="bg-emerald-50/40">
                  <th scope="row" className="py-2.5 px-3 font-bold text-emerald-950">
                    {evalReport.comparison_summary.proposed_b_misconception_aware.method}
                  </th>
                  <td className="py-2.5 px-3 font-mono font-bold text-emerald-900">
                    {(
                      evalReport.comparison_summary.proposed_b_misconception_aware
                        .recommendation_relevance_rate * 100
                    ).toFixed(1)}
                    %
                  </td>
                  <td className="py-2.5 px-3 font-mono font-bold text-emerald-900">
                    {(
                      evalReport.comparison_summary.proposed_b_misconception_aware
                        .simulated_immediate_verification_accuracy * 100
                    ).toFixed(1)}
                    %
                  </td>
                  <td className="py-2.5 px-3 font-mono font-bold text-emerald-900">
                    {(
                      evalReport.comparison_summary.proposed_b_misconception_aware
                        .simulated_error_recurrence_rate * 100
                    ).toFixed(1)}
                    %
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
};
