import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuthScreen } from '../components/AuthScreen';
import { Navbar } from '../components/Navbar';
import { UserProfile } from '../types/api';

const sampleStudent: UserProfile = {
  id: 1,
  email: 'aarav.student@demo.learnwhy.edu',
  full_name: 'Aarav Sharma',
  role: 'student',
  status: 'active',
  onboarding_completed: true,
  selected_course_id: 1,
  points: 85,
  current_streak: 3,
  daily_goal_minutes: 20,
  streak_opt_in: true,
  preferences: {
    language: 'en',
    text_size: 'normal',
    reduced_motion: false,
    high_contrast: false,
    plain_language_mode: false,
    preferred_formats: ['text', 'diagram', 'interactive'],
  },
};

const sampleEducator: UserProfile = {
  ...sampleStudent,
  id: 4,
  email: 'meera.educator@demo.learnwhy.edu',
  full_name: 'Prof. Meera Krishnan',
  role: 'educator',
};

describe('LearnWhy AI Frontend Accessibility & Role Navigation Tests', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders accessible AuthScreen with labeled form controls and all 6 official considerations', () => {
    render(<AuthScreen onAuthenticated={() => {}} />);

    expect(screen.getByText('LearnWhy AI')).toBeInTheDocument();
    expect(screen.getByLabelText('Email Address')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByText('1. Adaptive Learning Models')).toBeInTheDocument();
    expect(screen.getByText('2. Intelligent Tutoring System')).toBeInTheDocument();
    expect(screen.getByText('3. Supportive Gamification')).toBeInTheDocument();
    expect(screen.getByText('4. Multimodal Learning')).toBeInTheDocument();
    expect(screen.getByText('5. Accessibility & Inclusivity')).toBeInTheDocument();
    expect(screen.getByText('6. Educator Insights & Research')).toBeInTheDocument();
  });

  it('hides Insights and Admin tabs for student role and exposes accessibility toggles', () => {
    render(
      <Navbar
        user={sampleStudent}
        activeTab="home"
        onSelectTab={() => {}}
        onOpenSettings={() => {}}
        onQuickToggleTextSize={() => {}}
        onQuickTogglePlainLanguage={() => {}}
        onLogout={() => {}}
      />
    );

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Learn')).toBeInTheDocument();
    expect(screen.getByText('Progress')).toBeInTheDocument();
    expect(screen.queryByText('Insights')).not.toBeInTheDocument();
    expect(screen.queryByText('Content & Rules')).not.toBeInTheDocument();
    expect(screen.getByText('Plain Text: OFF')).toBeInTheDocument();
  });

  it('exposes Insights tab for educator role', () => {
    render(
      <Navbar
        user={sampleEducator}
        activeTab="insights"
        onSelectTab={() => {}}
        onOpenSettings={() => {}}
        onQuickToggleTextSize={() => {}}
        onQuickTogglePlainLanguage={() => {}}
        onLogout={() => {}}
      />
    );

    expect(screen.getByText('Insights')).toBeInTheDocument();
  });
});
