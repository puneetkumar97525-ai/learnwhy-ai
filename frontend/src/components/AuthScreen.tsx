import React, { useState } from 'react';
import {
  BookOpen,
  CheckCircle2,
  ShieldCheck,
  Sparkles,
  UserCheck,
  GraduationCap,
  Settings2,
  AlertCircle,
} from 'lucide-react';
import { api, setStoredToken } from '../services/api';
import { UserProfile } from '../types/api';

interface AuthScreenProps {
  onAuthenticated: (user: UserProfile) => void;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({ onAuthenticated }) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('aarav.student@demo.learnwhy.edu');
  const [password, setPassword] = useState('StudentPass123!');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<'student' | 'educator' | 'admin'>('student');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res =
        mode === 'login'
          ? await api.login(email, password)
          : await api.register(email, password, fullName || 'Python Learner', role);
      setStoredToken(res.access_token);
      onAuthenticated(res.user);
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoQuickLogin = async (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(demoEmail, demoPass);
      setStoredToken(res.access_token);
      onAuthenticated(res.user);
    } catch (err: any) {
      setError(err?.message || 'Demo sign-in failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
        {/* Top Banner */}
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-indigo-700 text-white flex items-center justify-center font-bold text-xl shadow-sm">
              LW
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                LearnWhy AI
              </h1>
              <p className="text-sm text-slate-600">
                Official Problem Statement PSM147 (Serial 47) • PS Number QE4 • Quality Education
              </p>
            </div>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-xs font-semibold text-indigo-900">
            <Sparkles className="w-4 h-4 text-indigo-700" aria-hidden="true" />
            <span>Misconception-Aware Knowledge Tracing & Adaptive Remediation</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left column: Product Overview & 6 Mandatory Considerations */}
          <section
            aria-label="Platform capabilities overview"
            className="lg:col-span-7 space-y-6"
          >
            <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-4">
              <span className="inline-block text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-md border border-indigo-200">
                Python Programming Education MVP
              </span>
              <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 leading-tight">
                Understand <em>why</em> an answer went wrong, practice what matters next, and verify your progress.
              </h2>
              <p className="text-slate-700 leading-relaxed">
                LearnWhy AI replaces one-size-fits-all quizzes with a transparent{' '}
                <strong>
                  Diagnose → Follow-Up (when ambiguous) → Explainable Intervention → Fresh Verification
                </strong>{' '}
                loop. Every concept mastery estimate, misconception hypothesis, and recommendation score is inspectable.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {[
                  {
                    title: '1. Adaptive Learning Models',
                    desc: 'Concept-level mastery estimates in [0,1], prerequisite graph checks, and adaptive difficulty.',
                  },
                  {
                    title: '2. Intelligent Tutoring System',
                    desc: 'Progressive hint ladder, worked examples, and deterministic answer keys that work without an LLM.',
                  },
                  {
                    title: '3. Supportive Gamification',
                    desc: 'Points, badges, and optional streaks that reward effort without penalizing accessibility needs.',
                  },
                  {
                    title: '4. Multimodal Learning',
                    desc: 'Selectable text, annotated Python code, SVG flowcharts, audio narration + transcripts, and interactive checks.',
                  },
                  {
                    title: '5. Accessibility & Inclusivity',
                    desc: 'Keyboard-operable UI, scalable text, plain-language & bilingual support, and non-color-only cues.',
                  },
                  {
                    title: '6. Educator Insights & Research',
                    desc: 'Class concept heatmaps, common misconceptions, explainable review alerts, CSV export, and baseline evaluation.',
                  },
                ].map((item) => (
                  <div
                    key={item.title}
                    className="p-3.5 rounded-xl bg-slate-50 border border-slate-200"
                  >
                    <div className="flex items-center gap-2 font-semibold text-sm text-slate-900">
                      <CheckCircle2
                        className="w-4 h-4 text-emerald-700 shrink-0"
                        aria-hidden="true"
                      />
                      <span>{item.title}</span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* One-Click Demo Role Switcher */}
            <div className="bg-indigo-950 text-white rounded-2xl p-6 border border-indigo-800 shadow-sm space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <h3 className="font-bold text-base flex items-center gap-2">
                    <UserCheck className="w-5 h-5 text-indigo-300" aria-hidden="true" />
                    <span>Instant Demo Role Access (Seeded Sample Accounts)</span>
                  </h3>
                  <p className="text-xs text-indigo-200 mt-0.5">
                    Click any role below to sign in immediately with realistic, pre-seeded sample data.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() =>
                    handleDemoQuickLogin(
                      'aarav.student@demo.learnwhy.edu',
                      'StudentPass123!'
                    )
                  }
                  className="text-left p-3.5 rounded-xl bg-indigo-900/90 hover:bg-indigo-800 border border-indigo-700 transition-colors"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-300">
                    <BookOpen className="w-4 h-4" aria-hidden="true" />
                    <span>Student Role</span>
                  </div>
                  <div className="font-semibold text-sm mt-1">Aarav Sharma</div>
                  <div className="text-xs text-indigo-200 mt-0.5">
                    Full learning loop, hints, follow-ups & progress
                  </div>
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() =>
                    handleDemoQuickLogin(
                      'meera.educator@demo.learnwhy.edu',
                      'EducatorPass123!'
                    )
                  }
                  className="text-left p-3.5 rounded-xl bg-indigo-900/90 hover:bg-indigo-800 border border-indigo-700 transition-colors"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-amber-300">
                    <GraduationCap className="w-4 h-4" aria-hidden="true" />
                    <span>Educator Role</span>
                  </div>
                  <div className="font-semibold text-sm mt-1">Prof. Meera Krishnan</div>
                  <div className="text-xs text-indigo-200 mt-0.5">
                    Class analytics, alerts, CSV export & baseline eval
                  </div>
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() =>
                    handleDemoQuickLogin(
                      'vikram.admin@demo.learnwhy.edu',
                      'AdminPass123!'
                    )
                  }
                  className="text-left p-3.5 rounded-xl bg-indigo-900/90 hover:bg-indigo-800 border border-indigo-700 transition-colors"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-sky-300">
                    <Settings2 className="w-4 h-4" aria-hidden="true" />
                    <span>Admin Role</span>
                  </div>
                  <div className="font-semibold text-sm mt-1">Vikram Desai</div>
                  <div className="text-xs text-indigo-200 mt-0.5">
                    Manage questions, rules, concepts & audit logs
                  </div>
                </button>
              </div>
            </div>
          </section>

          {/* Right column: Accessible Sign-In / Registration Card */}
          <section
            aria-label="Sign in or create an account"
            className="lg:col-span-5 bg-white rounded-2xl p-6 sm:p-8 border border-slate-200 shadow-sm"
          >
            <div className="flex rounded-xl bg-slate-100 p-1 mb-6" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'login'}
                onClick={() => {
                  setMode('login');
                  setError(null);
                }}
                className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-colors ${
                  mode === 'login'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'register'}
                onClick={() => {
                  setMode('register');
                  setError(null);
                }}
                className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-colors ${
                  mode === 'register'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Create Account
              </button>
            </div>

            {error && (
              <div
                role="alert"
                className="mb-4 p-3.5 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-sm flex items-start gap-2.5"
              >
                <AlertCircle className="w-5 h-5 text-rose-700 shrink-0 mt-0.5" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'register' && (
                <div>
                  <label
                    htmlFor="auth-fullname"
                    className="block text-sm font-semibold text-slate-800 mb-1"
                  >
                    Full Name
                  </label>
                  <input
                    id="auth-fullname"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g., Ananya Gupta"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-slate-900 text-sm focus:border-indigo-600"
                  />
                </div>
              )}

              <div>
                <label
                  htmlFor="auth-email"
                  className="block text-sm font-semibold text-slate-800 mb-1"
                >
                  Email Address
                </label>
                <input
                  id="auth-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-slate-900 text-sm focus:border-indigo-600"
                />
              </div>

              <div>
                <label
                  htmlFor="auth-password"
                  className="block text-sm font-semibold text-slate-800 mb-1"
                >
                  Password
                </label>
                <input
                  id="auth-password"
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-slate-900 text-sm focus:border-indigo-600"
                />
              </div>

              {mode === 'register' && (
                <div>
                  <label
                    htmlFor="auth-role"
                    className="block text-sm font-semibold text-slate-800 mb-1"
                  >
                    Account Role
                  </label>
                  <select
                    id="auth-role"
                    value={role}
                    onChange={(e) => setRole(e.target.value as any)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-slate-900 text-sm bg-white"
                  >
                    <option value="student">Student / Learner</option>
                    <option value="educator">Educator / Instructor</option>
                    <option value="admin">Administrator / Content Manager</option>
                  </select>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-xl bg-indigo-700 hover:bg-indigo-800 disabled:opacity-60 text-white font-semibold text-sm shadow-sm transition-colors"
              >
                {loading
                  ? 'Authenticating...'
                  : mode === 'login'
                  ? 'Sign In to LearnWhy AI'
                  : 'Create Account & Start Learning'}
              </button>
            </form>

            <div className="mt-6 pt-5 border-t border-slate-200 text-xs text-slate-600 space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                <ShieldCheck className="w-4 h-4 text-emerald-700" aria-hidden="true" />
                <span>Privacy & Transparency Notice</span>
              </div>
              <p>
                Passwords are stored as salted bcrypt hashes. Concept mastery values are heuristic estimates used to personalize practice, never permanent ability scores.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
