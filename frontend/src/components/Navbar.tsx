import React from 'react';
import {
  BookOpen,
  Compass,
  BarChart3,
  GraduationCap,
  ShieldCheck,
  Settings,
  LogOut,
  Award,
  Flame,
  Type,
  Eye,
} from 'lucide-react';
import { UserProfile } from '../types/api';

export type NavTab = 'home' | 'learn' | 'progress' | 'insights' | 'admin';

interface NavbarProps {
  user: UserProfile;
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  onOpenSettings: () => void;
  onQuickToggleTextSize: () => void;
  onQuickTogglePlainLanguage: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  activeTab,
  onSelectTab,
  onOpenSettings,
  onQuickToggleTextSize,
  onQuickTogglePlainLanguage,
  onLogout,
}) => {
  const canViewInsights = user.role === 'educator' || user.role === 'admin';
  const canViewAdmin = user.role === 'admin';
  const isBilingual = user.preferences?.language === 'bilingual' || user.preferences?.language === 'hi';

  const navItems: Array<{ id: NavTab; label: string; hiLabel: string; icon: React.ReactNode }> = [
    { id: 'home', label: 'Home', hiLabel: 'मुख्य पृष्ठ', icon: <Compass className="w-4 h-4" aria-hidden="true" /> },
    { id: 'learn', label: 'Learn', hiLabel: 'सीखें', icon: <BookOpen className="w-4 h-4" aria-hidden="true" /> },
    { id: 'progress', label: 'Progress', hiLabel: 'प्रगति', icon: <BarChart3 className="w-4 h-4" aria-hidden="true" /> },
  ];

  if (canViewInsights) {
    navItems.push({
      id: 'insights',
      label: 'Insights',
      hiLabel: 'शिक्षक विश्लेषण',
      icon: <GraduationCap className="w-4 h-4" aria-hidden="true" />,
    });
  }

  if (canViewAdmin) {
    navItems.push({
      id: 'admin',
      label: 'Content & Rules',
      hiLabel: 'प्रबंधन',
      icon: <ShieldCheck className="w-4 h-4" aria-hidden="true" />,
    });
  }

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-sm hc-card">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between py-3 gap-3">
          {/* Brand identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-700 text-white flex items-center justify-center font-bold text-lg shadow-sm">
              LW
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 tracking-tight text-lg">
                  LearnWhy AI
                </span>
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
                  PSM147 • QE4
                </span>
              </div>
              <p className="text-xs text-slate-600 hidden sm:block">
                Explainable, Misconception-Aware Python Learning
              </p>
            </div>
          </div>

          {/* Primary Navigation */}
          <nav aria-label="Main navigation" className="flex items-center gap-1 sm:gap-2 flex-wrap">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectTab(item.id)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-700 text-white shadow-sm'
                      : 'text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {item.icon}
                  <span>{isBilingual ? `${item.label} (${item.hiLabel})` : item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Gamification stats + Accessibility controls + Profile */}
          <div className="flex items-center gap-2 flex-wrap">
            <div
              className="hidden md:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-xs font-medium text-slate-800"
              aria-label={`Gamification summary: ${user.points} points`}
            >
              <span className="inline-flex items-center gap-1 text-amber-800">
                <Award className="w-4 h-4 text-amber-600" aria-hidden="true" />
                <span>{user.points} pts</span>
              </span>
              {user.streak_opt_in && (
                <span className="inline-flex items-center gap-1 text-emerald-800 border-l border-slate-300 pl-2">
                  <Flame className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                  <span>{user.current_streak}d pace</span>
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={onQuickToggleTextSize}
              title="Cycle scalable text size (Normal / Large / Extra Large)"
              aria-label={`Text size: ${user.preferences?.text_size || 'normal'}. Click to change.`}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-800"
            >
              <Type className="w-3.5 h-3.5 text-indigo-700" aria-hidden="true" />
              <span>
                {user.preferences?.text_size === 'xlarge'
                  ? 'A++'
                  : user.preferences?.text_size === 'large'
                  ? 'A+'
                  : 'A'}
              </span>
            </button>

            <button
              type="button"
              onClick={onQuickTogglePlainLanguage}
              aria-pressed={Boolean(user.preferences?.plain_language_mode)}
              title="Toggle plain-language explanations"
              className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-xs font-semibold ${
                user.preferences?.plain_language_mode
                  ? 'bg-emerald-50 border-emerald-400 text-emerald-900'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <Eye className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Plain Text: {user.preferences?.plain_language_mode ? 'ON' : 'OFF'}</span>
            </button>

            <button
              type="button"
              onClick={onOpenSettings}
              aria-label="Open accessibility, format preferences, and privacy settings"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-medium text-slate-800"
            >
              <Settings className="w-4 h-4 text-slate-600" aria-hidden="true" />
              <span className="hidden sm:inline">Preferences</span>
            </button>

            <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
              <div className="text-right hidden lg:block">
                <div className="text-xs font-semibold text-slate-900 leading-tight">
                  {user.full_name}
                </div>
                <div className="text-[11px] uppercase tracking-wider font-semibold text-indigo-700">
                  Role: {user.role}
                </div>
              </div>
              <button
                type="button"
                onClick={onLogout}
                aria-label="Sign out"
                title="Sign out"
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-800 border border-slate-200 text-xs font-medium"
              >
                <LogOut className="w-4 h-4" aria-hidden="true" />
                <span className="sr-only sm:not-sr-only">Sign out</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
