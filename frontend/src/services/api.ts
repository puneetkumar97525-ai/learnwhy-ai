import { UserProfile } from '../types/api';

const TOKEN_KEY = 'learnwhy_access_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(path, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errBody = await res.json();
      if (errBody?.detail) {
        detail =
          typeof errBody.detail === 'string'
            ? errBody.detail
            : JSON.stringify(errBody.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    apiRequest<{ access_token: string; user: UserProfile }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (
    email: string,
    password: string,
    full_name: string,
    role: string = 'student'
  ) =>
    apiRequest<{ access_token: string; user: UserProfile }>(
      '/api/auth/register',
      {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name, role }),
      }
    ),

  getMe: () => apiRequest<{ user: UserProfile }>('/api/auth/me'),

  updatePreferences: (payload: Record<string, unknown>) =>
    apiRequest<{ user: UserProfile }>('/api/auth/preferences', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  exportMyData: () => apiRequest<Record<string, unknown>>('/api/auth/export-my-data'),

  getCourses: () => apiRequest<{ courses: Array<{ id: number; slug: string; title: string; description: string; concepts_count: number }> }>('/api/courses'),

  getCourseConcepts: (courseId: number) =>
    apiRequest<any>(`/api/courses/${courseId}/concepts`),

  getNextQuestion: (conceptId?: number | null, excludeQuestionId?: number | null) => {
    const params = new URLSearchParams();
    if (conceptId) params.set('concept_id', String(conceptId));
    if (excludeQuestionId) params.set('exclude_question_id', String(excludeQuestionId));
    const qs = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<any>(`/api/questions/next${qs}`);
  },

  getQuestionHint: (questionId: number, hintIndex: number) =>
    apiRequest<any>(`/api/questions/${questionId}/hint?hint_index=${hintIndex}`),

  submitAttempt: (question_id: number, response: string, hints_used: number = 0) =>
    apiRequest<any>('/api/attempts', {
      method: 'POST',
      body: JSON.stringify({ question_id, response, hints_used, attempt_context: 'practice' }),
    }),

  submitDiagnosticFollowup: (
    attemptId: number,
    followup_question_id: number,
    response: string
  ) =>
    apiRequest<any>(`/api/attempts/${attemptId}/diagnostic-follow-up`, {
      method: 'POST',
      body: JSON.stringify({ followup_question_id, response }),
    }),

  getRecommendations: (strategy: 'proposed' | 'baseline_score' = 'proposed', refresh: boolean = true) =>
    apiRequest<any>(`/api/recommendations?strategy=${strategy}&refresh=${refresh}`),

  completeIntervention: (
    recommendationId: number,
    completion_seconds: number = 120,
    format_used: string = 'multimodal'
  ) =>
    apiRequest<any>(`/api/interventions/${recommendationId}/complete`, {
      method: 'POST',
      body: JSON.stringify({ completion_seconds, format_used }),
    }),

  verifyIntervention: (
    recommendationId: number,
    verification_question_id: number,
    response: string,
    completion_seconds: number = 75
  ) =>
    apiRequest<any>(`/api/interventions/${recommendationId}/verify`, {
      method: 'POST',
      body: JSON.stringify({
        verification_question_id,
        response,
        completion_seconds,
      }),
    }),

  getProgressSummary: () => apiRequest<any>('/api/progress/summary'),

  getEducatorAnalytics: (classId: number = 1, conceptId?: number | null) => {
    const qs = conceptId ? `?concept_id=${conceptId}` : '';
    return apiRequest<any>(`/api/educator/classes/${classId}/analytics${qs}`);
  },

  acknowledgeEducatorAlert: (
    classId: number,
    outcome_id: number,
    educator_note: string
  ) =>
    apiRequest<any>(`/api/educator/classes/${classId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ outcome_id, educator_note, acknowledged: true }),
    }),

  downloadEducatorCsv: async (classId: number = 1): Promise<string> => {
    const token = getStoredToken();
    const res = await fetch(`/api/educator/classes/${classId}/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      throw new Error(`Export failed (${res.status})`);
    }
    return res.text();
  },

  getEvaluationReport: () => apiRequest<any>('/api/evaluation/report'),

  getAdminOverview: () => apiRequest<any>('/api/admin/overview'),

  adminCreateQuestion: (payload: Record<string, unknown>) =>
    apiRequest<any>('/api/admin/questions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  adminArchiveQuestion: (questionId: number) =>
    apiRequest<any>(`/api/admin/questions/${questionId}/archive`, {
      method: 'POST',
    }),

  adminCreateMisconception: (payload: Record<string, unknown>) =>
    apiRequest<any>('/api/admin/misconceptions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  adminCreateActivity: (payload: Record<string, unknown>) =>
    apiRequest<any>('/api/admin/activities', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  adminCreateConcept: (payload: Record<string, unknown>) =>
    apiRequest<any>('/api/admin/concepts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
