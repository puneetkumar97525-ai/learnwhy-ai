import React, { useState } from 'react';
import {
  CheckCircle2,
  Download,
  Eye,
  ShieldCheck,
  Sliders,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { UserProfile } from '../types/api';

interface SettingsPrivacyModalProps {
  user: UserProfile;
  onClose: () => void;
  onUpdated: (updatedUser: UserProfile) => void;
}

export const SettingsPrivacyModal: React.FC<SettingsPrivacyModalProps> = ({
  user,
  onClose,
  onUpdated,
}) => {
  const [language, setLanguage] = useState<'en' | 'hi' | 'bilingual'>(
    user.preferences?.language || 'en'
  );
  const [textSize, setTextSize] = useState<'normal' | 'large' | 'xlarge'>(
    user.preferences?.text_size || 'normal'
  );
  const [reducedMotion, setReducedMotion] = useState<boolean>(
    Boolean(user.preferences?.reduced_motion)
  );
  const [highContrast, setHighContrast] = useState<boolean>(
    Boolean(user.preferences?.high_contrast)
  );
  const [plainLanguage, setPlainLanguage] = useState<boolean>(
    Boolean(user.preferences?.plain_language_mode)
  );
  const [preferredFormats, setPreferredFormats] = useState<string[]>(
    user.preferences?.preferred_formats || ['text', 'diagram', 'interactive']
  );
  const [dailyGoal, setDailyGoal] = useState<number>(
    user.daily_goal_minutes || 20
  );
  const [streakOptIn, setStreakOptIn] = useState<boolean>(
    user.streak_opt_in !== false
  );
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const toggleFormat = (fmt: string) => {
    setPreferredFormats((prev) =>
      prev.includes(fmt) ? prev.filter((x) => x !== fmt) : [...prev, fmt]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedMsg(null);
    try {
      const res = await api.updatePreferences({
        selected_course_id: user.selected_course_id || 1,
        language,
        text_size: textSize,
        reduced_motion: reducedMotion,
        high_contrast: highContrast,
        plain_language_mode: plainLanguage,
        preferred_formats:
          preferredFormats.length > 0 ? preferredFormats : ['text'],
        daily_goal_minutes: dailyGoal,
        streak_opt_in: streakOptIn,
        onboarding_completed: true,
      });
      onUpdated(res.user);
      setSavedMsg('Preferences saved and applied immediately.');
    } finally {
      setSaving(false);
    }
  };

  const handleExportMyData = async () => {
    const data = await api.exportMyData();
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `learnwhy_my_learning_data_${user.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-modal-title"
      className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4 overflow-y-auto"
    >
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 sm:p-8 border border-slate-200 shadow-xl space-y-6 hc-card">
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-indigo-700" aria-hidden="true" />
            <h2
              id="settings-modal-title"
              className="text-xl font-bold text-slate-900"
            >
              Accessibility, Format Preferences &amp; Privacy
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close preferences dialog"
            className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {savedMsg && (
          <div
            role="status"
            className="p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-xs font-semibold flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-700" aria-hidden="true" />
            <span>{savedMsg}</span>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-5 text-xs sm:text-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="pref-language"
                className="block font-semibold text-slate-800 mb-1"
              >
                Interface &amp; Explanation Language
              </label>
              <select
                id="pref-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white"
              >
                <option value="en">English</option>
                <option value="bilingual">Bilingual (English + Hindi Terms)</option>
                <option value="hi">Hindi Support Mode</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="pref-textsize"
                className="block font-semibold text-slate-800 mb-1"
              >
                Scalable Text Size (SRC-5)
              </label>
              <select
                id="pref-textsize"
                value={textSize}
                onChange={(e) => setTextSize(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white"
              >
                <option value="normal">Normal (100%)</option>
                <option value="large">Large (112.5%)</option>
                <option value="xlarge">Extra Large (125%)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={plainLanguage}
                onChange={(e) => setPlainLanguage(e.target.checked)}
                className="h-4 w-4"
              />
              <span className="font-semibold text-slate-800">
                Plain-Language Explanations
              </span>
            </label>

            <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={reducedMotion}
                onChange={(e) => setReducedMotion(e.target.checked)}
                className="h-4 w-4"
              />
              <span className="font-semibold text-slate-800">
                Reduced Motion
              </span>
            </label>

            <label className="flex items-center gap-2.5 p-3 rounded-xl border border-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={highContrast}
                onChange={(e) => setHighContrast(e.target.checked)}
                className="h-4 w-4"
              />
              <span className="font-semibold text-slate-800">
                High Contrast Borders
              </span>
            </label>
          </div>

          {/* Multimodal Format Preferences */}
          <fieldset className="space-y-2">
            <legend className="font-semibold text-slate-800">
              Preferred Presentation Formats (Selectable options, not fixed learning-style labels):
            </legend>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { id: 'text', label: 'Text & Code' },
                { id: 'diagram', label: 'SVG Flowcharts' },
                { id: 'interactive', label: 'Interactive Check' },
                { id: 'audio', label: 'Audio + Transcript' },
              ].map((f) => (
                <label
                  key={f.id}
                  className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-300 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={preferredFormats.includes(f.id)}
                    onChange={() => toggleFormat(f.id)}
                    className="h-4 w-4"
                  />
                  <span>{f.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {/* Supportive Gamification Preferences */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-200">
            <div>
              <label
                htmlFor="pref-goal"
                className="block font-semibold text-slate-800 mb-1"
              >
                Daily Practice Goal (Minutes)
              </label>
              <input
                id="pref-goal"
                type="number"
                min={5}
                max={120}
                value={dailyGoal}
                onChange={(e) => setDailyGoal(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-xl border border-slate-300"
              />
            </div>

            <div className="flex items-end">
              <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-300 w-full cursor-pointer">
                <input
                  type="checkbox"
                  checked={streakOptIn}
                  onChange={(e) => setStreakOptIn(e.target.checked)}
                  className="h-4 w-4"
                />
                <span>
                  Show optional daily streak counter (Pause anytime without penalty)
                </span>
              </label>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={handleExportMyData}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-800 font-semibold text-xs"
            >
              <Download className="w-4 h-4 text-indigo-700" aria-hidden="true" />
              <span>Export My Learning Data (JSON)</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl border border-slate-300 text-slate-700 font-semibold text-xs"
              >
                Close
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2 rounded-xl bg-indigo-700 hover:bg-indigo-800 text-white font-semibold text-xs"
              >
                {saving ? 'Saving...' : 'Save Preferences'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
