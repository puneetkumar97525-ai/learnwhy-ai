import React, { useEffect, useState } from 'react';
import { AuthScreen } from './components/AuthScreen';
import { Navbar, NavTab } from './components/Navbar';
import { HomeView } from './components/HomeView';
import { LearnWorkspace } from './components/LearnWorkspace';
import { ProgressView } from './components/ProgressView';
import { EducatorInsightsView } from './components/EducatorInsightsView';
import { AdminStudioView } from './components/AdminStudioView';
import { SettingsPrivacyModal } from './components/SettingsPrivacyModal';
import { api, getStoredToken, setStoredToken } from './services/api';
import { RecommendationItem, UserProfile } from './types/api';

export function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [activeTab, setActiveTab] = useState<NavTab>('home');
  const [learnConceptId, setLearnConceptId] = useState<number | null>(null);
  const [learnRecommendation, setLearnRecommendation] =
    useState<RecommendationItem | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const fetchCurrentUser = async () => {
    try {
      const res = await api.getMe();
      setUser(res.user);
    } catch {
      setStoredToken(null);
      setUser(null);
    } finally {
      setInitializing(false);
    }
  };

  useEffect(() => {
    if (getStoredToken()) {
      fetchCurrentUser();
    } else {
      setInitializing(false);
    }
  }, []);

  const handleAuthenticated = (loggedInUser: UserProfile) => {
    setUser(loggedInUser);
    if (loggedInUser.role === 'educator') {
      setActiveTab('insights');
    } else if (loggedInUser.role === 'admin') {
      setActiveTab('admin');
    } else {
      setActiveTab('home');
    }
  };

  const handleLogout = () => {
    setStoredToken(null);
    setUser(null);
    setActiveTab('home');
  };

  const handleQuickToggleTextSize = async () => {
    if (!user) return;
    const order: Array<'normal' | 'large' | 'xlarge'> = [
      'normal',
      'large',
      'xlarge',
    ];
    const current = user.preferences?.text_size || 'normal';
    const next = order[(order.indexOf(current) + 1) % order.length];
    try {
      const res = await api.updatePreferences({
        ...user.preferences,
        selected_course_id: user.selected_course_id || 1,
        text_size: next,
        daily_goal_minutes: user.daily_goal_minutes,
        streak_opt_in: user.streak_opt_in,
      });
      setUser(res.user);
    } catch {
      // ignore
    }
  };

  const handleQuickTogglePlainLanguage = async () => {
    if (!user) return;
    const next = !user.preferences?.plain_language_mode;
    try {
      const res = await api.updatePreferences({
        ...user.preferences,
        selected_course_id: user.selected_course_id || 1,
        plain_language_mode: next,
        daily_goal_minutes: user.daily_goal_minutes,
        streak_opt_in: user.streak_opt_in,
      });
      setUser(res.user);
    } catch {
      // ignore
    }
  };

  if (initializing) {
    return (
      <div
        role="status"
        className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-700 text-sm font-medium"
      >
        Initializing LearnWhy AI...
      </div>
    );
  }

  if (!user) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  const textScaleClass =
    user.preferences?.text_size === 'xlarge'
      ? 'text-scale-xlarge'
      : user.preferences?.text_size === 'large'
      ? 'text-scale-large'
      : 'text-scale-normal';

  const reduceMotionClass = user.preferences?.reduced_motion
    ? 'reduce-motion'
    : '';
  const highContrastClass = user.preferences?.high_contrast
    ? 'high-contrast-mode'
    : '';

  return (
    <div
      className={`min-h-screen flex flex-col bg-slate-50 text-slate-900 ${textScaleClass} ${reduceMotionClass} ${highContrastClass}`}
    >
      {/* Skip-to-main-content link for keyboard & screen-reader users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:rounded-lg focus:bg-indigo-700 focus:text-white focus:font-semibold"
      >
        Skip to main content
      </a>

      <Navbar
        user={user}
        activeTab={activeTab}
        onSelectTab={(tab) => {
          if (tab === 'learn') {
            setLearnRecommendation(null);
          }
          setActiveTab(tab);
        }}
        onOpenSettings={() => setSettingsOpen(true)}
        onQuickToggleTextSize={handleQuickToggleTextSize}
        onQuickTogglePlainLanguage={handleQuickTogglePlainLanguage}
        onLogout={handleLogout}
      />

      <main
        id="main-content"
        tabIndex={-1}
        className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8"
      >
        {activeTab === 'home' && (
          <HomeView
            user={user}
            onStartPractice={(cid) => {
              setLearnConceptId(cid || null);
              setLearnRecommendation(null);
              setActiveTab('learn');
            }}
            onStartRecommendation={(rec) => {
              setLearnRecommendation(rec);
              setActiveTab('learn');
            }}
          />
        )}

        {activeTab === 'learn' && (
          <LearnWorkspace
            user={user}
            initialConceptId={learnConceptId}
            initialRecommendation={learnRecommendation}
            onUserPointsUpdated={fetchCurrentUser}
          />
        )}

        {activeTab === 'progress' && <ProgressView />}

        {activeTab === 'insights' &&
          (user.role === 'educator' || user.role === 'admin') && (
            <EducatorInsightsView />
          )}

        {activeTab === 'admin' && user.role === 'admin' && <AdminStudioView />}
      </main>

      <footer className="bg-white border-t border-slate-200 py-5 mt-12 text-xs text-slate-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <strong>LearnWhy AI</strong> • Official Source Problem PSM147 (Serial 47) • PS Number QE4 • Theme: Quality Education
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span>Rule Engine: v1.0.0-rules</span>
            <span>•</span>
            <span>Mastery Model: EMA (alpha=0.20)</span>
            <span>•</span>
            <span>Core Tutor: Deterministic Curated Content</span>
          </div>
        </div>
      </footer>

      {settingsOpen && (
        <SettingsPrivacyModal
          user={user}
          onClose={() => setSettingsOpen(false)}
          onUpdated={(u) => setUser(u)}
        />
      )}
    </div>
  );
}
export default App;
