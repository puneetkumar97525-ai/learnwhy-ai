import React, { useEffect, useState } from 'react';
import {
  Archive,
  CheckCircle2,
  Database,
  FilePlus2,
  GitBranch,
  ListChecks,
  Plus,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../services/api';

export const AdminStudioView: React.FC = () => {
  const [overview, setOverview] = useState<any | null>(null);
  const [subTab, setSubTab] = useState<'questions' | 'misconceptions' | 'concepts' | 'audit'>('questions');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Question Form State
  const [qStableId, setQStableId] = useState('PY-VAR-03');
  const [qConceptId, setQConceptId] = useState<number>(1);
  const [qDifficulty, setQDifficulty] = useState<number>(1);
  const [qContent, setQContent] = useState('');
  const [qCode, setQCode] = useState('');
  const [qAnswerKey, setQAnswerKey] = useState('A');
  const [qExplanation, setQExplanation] = useState('');
  const [optA, setOptA] = useState('');
  const [optB, setOptB] = useState('');
  const [optBMiscId, setOptBMiscId] = useState<number | ''>('');

  // New Misconception Rule Form State
  const [mCode, setMCode] = useState('MISC-PY-CUSTOM-01');
  const [mConceptId, setMConceptId] = useState<number>(1);
  const [mLabel, setMLabel] = useState('');
  const [mDesc, setMDesc] = useState('');
  const [mRule, setMRule] = useState('');
  const [mFocus, setMFocus] = useState('');
  const [mVersion, setMVersion] = useState('v1.1.0-rules');

  const loadOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAdminOverview();
      setOverview(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load admin overview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, []);

  const handleCreateQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setStatusMessage(null);
    try {
      await api.adminCreateQuestion({
        stable_id: qStableId,
        concept_id: qConceptId,
        difficulty: qDifficulty,
        content: qContent,
        code_snippet: qCode || null,
        answer_key: qAnswerKey,
        explanation: qExplanation,
        hint_ladder: ['Trace each variable step by step before choosing an option.'],
        version: '1.1.0',
        status: 'published',
        options: [
          {
            option_key: 'A',
            option_text: optA || 'Correct option A',
            is_correct: qAnswerKey === 'A',
          },
          {
            option_key: 'B',
            option_text: optB || 'Distractor option B',
            misconception_id: optBMiscId ? Number(optBMiscId) : null,
            is_correct: qAnswerKey === 'B',
          },
        ],
      });
      setStatusMessage(`Created and published question ${qStableId}.`);
      setQContent('');
      setQCode('');
      setQExplanation('');
      loadOverview();
    } catch (err: any) {
      setError(err?.message || 'Failed to create question.');
    }
  };

  const handleArchiveQuestion = async (questionId: number, stableId: string) => {
    try {
      await api.adminArchiveQuestion(questionId);
      setStatusMessage(`Archived question ${stableId}.`);
      loadOverview();
    } catch (err: any) {
      setError(err?.message || 'Could not archive question.');
    }
  };

  const handleCreateMisconception = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setStatusMessage(null);
    try {
      await api.adminCreateMisconception({
        code: mCode,
        concept_id: mConceptId,
        label: mLabel,
        description: mDesc,
        diagnostic_rule: mRule,
        remediation_focus: mFocus,
        rule_version: mVersion,
        status: 'active',
      });
      setStatusMessage(`Created misconception rule ${mCode} (${mVersion}).`);
      setMLabel('');
      setMDesc('');
      setMRule('');
      setMFocus('');
      loadOverview();
    } catch (err: any) {
      setError(err?.message || 'Failed to create misconception rule.');
    }
  };

  if (loading) {
    return (
      <div
        role="status"
        className="p-8 bg-white rounded-2xl border border-slate-200 text-center text-sm text-slate-600"
      >
        Loading Admin Content &amp; Misconception Rule Studio...
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div
        role="alert"
        className="p-6 bg-rose-50 rounded-2xl border border-rose-300 text-rose-900"
      >
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header & Sub-navigation */}
      <section className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="inline-block text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-900 border border-indigo-200 mb-1.5">
            Admin Content &amp; Rule Versioning Studio (FR-19 / FR-20)
          </span>
          <h1 className="text-2xl font-bold text-slate-900">
            Curriculum, Question Bank &amp; Misconception Rule Manager
          </h1>
        </div>

        <div
          className="inline-flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1 text-xs"
          role="tablist"
        >
          {[
            { id: 'questions', label: `Question Bank (${overview.questions.length})` },
            { id: 'misconceptions', label: `Misconception Rules (${overview.misconceptions.length})` },
            { id: 'concepts', label: `Concepts & DAG (${overview.concepts.length})` },
            { id: 'audit', label: `Research & Audit Logs (${overview.audit_events.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={subTab === tab.id}
              onClick={() => setSubTab(tab.id as any)}
              className={`px-3 py-2 rounded-lg font-semibold ${
                subTab === tab.id
                  ? 'bg-white text-indigo-900 shadow-sm'
                  : 'text-slate-700 hover:text-slate-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {statusMessage && (
        <div
          role="status"
          className="p-4 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-sm font-semibold flex items-center gap-2"
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-700" aria-hidden="true" />
          <span>{statusMessage}</span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="p-4 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-sm font-semibold"
        >
          {error}
        </div>
      )}

      {/* TAB 1: QUESTION BANK CRUD */}
      {subTab === 'questions' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Create Question Form */}
          <form
            onSubmit={handleCreateQuestion}
            className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4"
          >
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <FilePlus2 className="w-5 h-5 text-indigo-700" aria-hidden="true" />
              <span>Add Curated Question</span>
            </h2>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="admin-q-sid" className="block text-xs font-semibold text-slate-700 mb-1">
                  Stable ID
                </label>
                <input
                  id="admin-q-sid"
                  type="text"
                  required
                  value={qStableId}
                  onChange={(e) => setQStableId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs font-mono"
                />
              </div>
              <div>
                <label htmlFor="admin-q-concept" className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Concept
                </label>
                <select
                  id="admin-q-concept"
                  value={qConceptId}
                  onChange={(e) => setQConceptId(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white"
                >
                  {overview.concepts.map((c: any) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="admin-q-diff" className="block text-xs font-semibold text-slate-700 mb-1">
                  Difficulty (1–3)
                </label>
                <select
                  id="admin-q-diff"
                  value={qDifficulty}
                  onChange={(e) => setQDifficulty(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white"
                >
                  <option value={1}>1 - Foundational</option>
                  <option value={2}>2 - Intermediate</option>
                  <option value={3}>3 - Applied</option>
                </select>
              </div>
              <div>
                <label htmlFor="admin-q-key" className="block text-xs font-semibold text-slate-700 mb-1">
                  Authoritative Answer Key
                </label>
                <select
                  id="admin-q-key"
                  value={qAnswerKey}
                  onChange={(e) => setQAnswerKey(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white"
                >
                  <option value="A">Option A</option>
                  <option value="B">Option B</option>
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="admin-q-content" className="block text-xs font-semibold text-slate-700 mb-1">
                Question Prompt
              </label>
              <textarea
                id="admin-q-content"
                required
                rows={2}
                value={qContent}
                onChange={(e) => setQContent(e.target.value)}
                placeholder="What is printed by the following Python snippet?"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
              />
            </div>

            <div>
              <label htmlFor="admin-q-code" className="block text-xs font-semibold text-slate-700 mb-1">
                Python Code Snippet (Optional)
              </label>
              <textarea
                id="admin-q-code"
                rows={2}
                value={qCode}
                onChange={(e) => setQCode(e.target.value)}
                placeholder="x = 5&#10;print(x * 2)"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs font-mono"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="admin-opt-a" className="block text-xs font-semibold text-slate-700 mb-1">
                  Option A Text
                </label>
                <input
                  id="admin-opt-a"
                  type="text"
                  required
                  value={optA}
                  onChange={(e) => setOptA(e.target.value)}
                  placeholder="10"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
                />
              </div>
              <div>
                <label htmlFor="admin-opt-b" className="block text-xs font-semibold text-slate-700 mb-1">
                  Option B Text
                </label>
                <input
                  id="admin-opt-b"
                  type="text"
                  required
                  value={optB}
                  onChange={(e) => setOptB(e.target.value)}
                  placeholder="55"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
                />
              </div>
            </div>

            <div>
              <label htmlFor="admin-opt-b-misc" className="block text-xs font-semibold text-slate-700 mb-1">
                Link Option B Distractor to Misconception Rule (Optional)
              </label>
              <select
                id="admin-opt-b-misc"
                value={optBMiscId}
                onChange={(e) => setOptBMiscId(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white"
              >
                <option value="">None (Unmapped / Insufficient Evidence)</option>
                {overview.misconceptions.map((m: any) => (
                  <option key={m.id} value={m.id}>
                    [{m.code}] {m.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="admin-q-exp" className="block text-xs font-semibold text-slate-700 mb-1">
                Curated Authoritative Explanation
              </label>
              <textarea
                id="admin-q-exp"
                required
                rows={2}
                value={qExplanation}
                onChange={(e) => setQExplanation(e.target.value)}
                placeholder="Explain step-by-step why the answer key is correct..."
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
              />
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 rounded-xl bg-indigo-700 hover:bg-indigo-800 text-white font-semibold text-xs"
            >
              Publish Question to Bank
            </button>
          </form>

          {/* Existing Questions List */}
          <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
            <h2 className="text-lg font-bold text-slate-900">
              Curated Question Bank ({overview.questions.length} items)
            </h2>
            <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
              {overview.questions.map((q: any) => (
                <div
                  key={q.id}
                  className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-indigo-900">
                        {q.stable_id}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-white border border-slate-300 font-semibold">
                        {q.concept_name} • L{q.difficulty}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded font-semibold ${
                          q.status === 'published'
                            ? 'bg-emerald-50 text-emerald-900 border border-emerald-300'
                            : 'bg-slate-200 text-slate-700'
                        }`}
                      >
                        {q.status} (v{q.version})
                      </span>
                    </div>
                    {q.status === 'published' && (
                      <button
                        type="button"
                        onClick={() => handleArchiveQuestion(q.id, q.stable_id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-rose-50 hover:bg-rose-100 text-rose-900 border border-rose-300 font-semibold"
                      >
                        <Archive className="w-3 h-3" aria-hidden="true" />
                        <span>Archive</span>
                      </button>
                    )}
                  </div>
                  <div className="font-semibold text-slate-900">{q.content}</div>
                  <div className="text-slate-600">
                    <strong>Answer Key:</strong> {q.answer_key} |{' '}
                    <strong>Explanation:</strong> {q.explanation}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: MISCONCEPTION RULES */}
      {subTab === 'misconceptions' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <form
            onSubmit={handleCreateMisconception}
            className="lg:col-span-5 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4"
          >
            <h2 className="text-lg font-bold text-slate-900">
              Add Versioned Misconception Rule
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="m-code" className="block text-xs font-semibold text-slate-700 mb-1">
                  Rule Code
                </label>
                <input
                  id="m-code"
                  type="text"
                  required
                  value={mCode}
                  onChange={(e) => setMCode(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs font-mono"
                />
              </div>
              <div>
                <label htmlFor="m-ver" className="block text-xs font-semibold text-slate-700 mb-1">
                  Rule Version
                </label>
                <input
                  id="m-ver"
                  type="text"
                  required
                  value={mVersion}
                  onChange={(e) => setMVersion(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs font-mono"
                />
              </div>
            </div>

            <div>
              <label htmlFor="m-concept" className="block text-xs font-semibold text-slate-700 mb-1">
                Concept
              </label>
              <select
                id="m-concept"
                value={mConceptId}
                onChange={(e) => setMConceptId(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs bg-white"
              >
                {overview.concepts.map((c: any) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="m-label" className="block text-xs font-semibold text-slate-700 mb-1">
                Misconception Label
              </label>
              <input
                id="m-label"
                type="text"
                required
                value={mLabel}
                onChange={(e) => setMLabel(e.target.value)}
                placeholder="e.g., Confusing == equality with = assignment"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
              />
            </div>

            <div>
              <label htmlFor="m-desc" className="block text-xs font-semibold text-slate-700 mb-1">
                Detailed Description
              </label>
              <textarea
                id="m-desc"
                required
                rows={2}
                value={mDesc}
                onChange={(e) => setMDesc(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
              />
            </div>

            <div>
              <label htmlFor="m-rule" className="block text-xs font-semibold text-slate-700 mb-1">
                Diagnostic Trigger Rule
              </label>
              <input
                id="m-rule"
                type="text"
                required
                value={mRule}
                onChange={(e) => setMRule(e.target.value)}
                placeholder="Selected distractor assumes single = compares values"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-xs"
              />
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 rounded-xl bg-indigo-700 hover:bg-indigo-800 text-white font-semibold text-xs"
            >
              Save Misconception Rule
            </button>
          </form>

          <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-3">
            <h2 className="text-lg font-bold text-slate-900">
              Active Misconception Rules
            </h2>
            <div className="space-y-3">
              {overview.misconceptions.map((m: any) => (
                <div
                  key={m.id}
                  className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between font-bold text-indigo-950">
                    <span>
                      [{m.code}] {m.label}
                    </span>
                    <span className="font-mono px-2 py-0.5 rounded bg-white border border-slate-300">
                      {m.rule_version}
                    </span>
                  </div>
                  <p className="text-slate-700">{m.description}</p>
                  <p className="text-slate-600">
                    <strong>Diagnostic Rule:</strong> {m.diagnostic_rule}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CONCEPTS & DAG */}
      {subTab === 'concepts' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <h2 className="text-lg font-bold text-slate-900">
            Course Concept Graph &amp; Prerequisite Links
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {overview.concepts.map((c: any) => (
              <div
                key={c.id}
                className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1"
              >
                <div className="font-bold text-sm text-slate-900">
                  {c.order_index}. {c.name} ({c.slug})
                </div>
                <p className="text-slate-700">{c.description}</p>
                <div className="text-slate-600 font-mono">
                  Prior Mastery: {c.prior_mastery} | Prerequisite IDs:{' '}
                  {c.prerequisite_ids.length > 0
                    ? c.prerequisite_ids.join(', ')
                    : 'None'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: RESEARCH & AUDIT LOGS */}
      {subTab === 'audit' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hc-card space-y-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Research &amp; Audit Event Trail (FR-20)
            </h2>
            <p className="text-xs text-slate-600">
              Stores rule/model version, diagnosis status, recommendation reasons, and content mutations. Passwords, tokens, and API keys are strictly excluded.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table
              aria-label="Research and content audit events"
              className="w-full text-left border-collapse text-xs"
            >
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-700">
                  <th scope="col" className="py-2 px-3 font-semibold">
                    Event Action
                  </th>
                  <th scope="col" className="py-2 px-3 font-semibold">
                    Actor Role
                  </th>
                  <th scope="col" className="py-2 px-3 font-semibold">
                    Entity
                  </th>
                  <th scope="col" className="py-2 px-3 font-semibold">
                    Rule Version
                  </th>
                  <th scope="col" className="py-2 px-3 font-semibold">
                    Sanitized Metadata
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {overview.audit_events.map((ev: any) => (
                  <tr key={ev.id}>
                    <td className="py-2 px-3 font-mono font-semibold text-indigo-900">
                      {ev.action}
                    </td>
                    <td className="py-2 px-3">{ev.actor_role || 'system'}</td>
                    <td className="py-2 px-3 font-mono">
                      {ev.entity_type} #{ev.entity_id}
                    </td>
                    <td className="py-2 px-3 font-mono">{ev.rule_version}</td>
                    <td className="py-2 px-3 font-mono text-[11px] text-slate-600">
                      {JSON.stringify(ev.metadata)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
