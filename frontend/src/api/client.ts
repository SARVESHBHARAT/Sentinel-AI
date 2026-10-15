/**
 * Sentinel AI API client
 * Wraps all backend endpoints with typed responses.
 */

const API_BASE = '/api';

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(
    status: number,
    detail: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail, detail);
  }

  // Handle empty responses (204, DELETE)
  const text = await res.text();
  if (!text) return {} as T;

  try {
    return JSON.parse(text) as T;
  } catch {
    return text as unknown as T;
  }
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Incident {
  incident_id: string;
  title: string;
  description: string;
  category: string;
  category_source: string;
  affected_system: string | null;
  provider: string | null;
  affected_model_name: string | null;
  affected_model_version: string | null;
  verification_status: string;
  occurrence_date: string | null;
  report_date: string;
  severity: string | null;
  severity_source: string | null;
  potential_impact: string | null;
  affected_population: string | null;
  anonymous_report: boolean;
  reporter_name: string | null;
  reporter_contact: string | null;
  assigned_reviewer: string | null;
  resolution_summary: string | null;
  status: string;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncidentListResponse {
  incidents: Incident[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface OverviewResponse {
  total: number;
  open_incidents: number;
  high_critical: number;
  awaiting_review: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_verification: Record<string, number>;
  trend: Record<string, number>;
}

export interface AIAssessment {
  incident_id: string;
  provider_mode: string;
  model_name: string;
  model_version: string | null;
  system_fingerprint: string | null;
  prompt_version: string;
  suggested_category: string;
  suggested_severity: string;
  risk_score: number;
  confidence: number;
  concise_summary: string;
  observed_failure_or_concern: string;
  potential_harms: string[];
  affected_stakeholders: string[];
  evidence: Array<{ report_reference: string; interpretation: string; is_factual_observation: boolean }>;
  missing_information: string[];
  immediate_containment_steps: string[];
  recommended_corrective_actions: string[];
  urgent_human_review_recommended: boolean;
  severity_explanation: string;
  created_at: string | null;
}

export interface AuditEvent {
  incident_id: string;
  event_type: string;
  actor: string | null;
  details: string | null;
  created_at: string | null;
}

export interface ReviewerNote {
  incident_id: string;
  body: string;
  author: string | null;
  created_at: string | null;
}

export interface CorrectiveAction {
  incident_id: string;
  title: string;
  action_kind: string;
  owner: string | null;
  status: string;
  due_date: string | null;
  evidence: string | null;
  created_at: string | null;
}

export interface ActivityResponse {
  audit_events: AuditEvent[];
  reviewer_notes: ReviewerNote[];
  corrective_actions: CorrectiveAction[];
}

export interface LeaderboardRow {
  provider: string;
  affected_model_name: string;
  version_label: string;
  total: number;
  verified: number;
  disputed: number;
  high_critical: number;
  verification_rate: number | null;
  most_common_category: string;
  most_recent_report: string;
  sufficient: boolean;
}

export interface ModelGroup {
  provider: string;
  affected_model_name: string;
  affected_model_version: string;
  total: number;
  severity: Record<string, number>;
  category: Record<string, number>;
  verification_status: Record<string, number>;
}

export interface ModelGroupsResponse {
  groups: ModelGroup[];
  total_matching_reports: number;
  min_sample: number;
  sufficient_data: boolean;
  note: string;
  formula: string;
}

export interface ModelOverviewMetrics {
  total: number;
  distinct_providers: number;
  distinct_models: number;
  distinct_versions: number;
  verified: number;
  disputed: number;
  high_critical: number;
  demo_records: number;
  genuine_records: number;
}

export interface VersionRow {
  affected_model_version: string;
  total: number;
  verified: number;
  high_critical: number;
  severity: Record<string, number>;
  category: Record<string, number>;
  verification_status: Record<string, number>;
  trend: Record<string, number>;
}

export interface ModelDetail {
  provider: string;
  affected_model_name: string;
  total: number;
  sufficient: boolean;
  versions: VersionRow[];
  recent_incidents: Incident[];
}

export interface SettingsResponse {
  demo_mode: boolean;
  effective_demo_mode: boolean;
  read_only: boolean;
  openai_model: string;
  has_api_key: boolean;
  model_intelligence_min_sample: number;
  submission_rate_limit: number;
  submission_rate_window_seconds: number;
  database_path: string;
}

export interface EnumsResponse {
  categories: string[];
  severities: string[];
  statuses: string[];
  verification_statuses: string[];
  category_sources: string[];
  severity_sources: string[];
}

// ─── API functions ─────────────────────────────────────────────────────────────

export const api = {
  health: () => request<{ status: string }>('/health'),

  overview: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<OverviewResponse>(`/overview${qs}`);
  },

  incidents: {
    list: (params: Record<string, string | number | boolean | undefined | null>) => {
      const clean: Record<string, string> = {};
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== '') clean[k] = String(v);
      }
      const qs = Object.keys(clean).length ? '?' + new URLSearchParams(clean).toString() : '';
      return request<IncidentListResponse>(`/incidents${qs}`);
    },

    get: (id: string) => request<Incident>(`/incidents/${id}`),

    create: (payload: Record<string, unknown>) =>
      request<Incident>('/incidents', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    update: (id: string, payload: Record<string, unknown>) =>
      request<Incident>(`/incidents/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),

    transition: (id: string, target_status: string, actor?: string) =>
      request<Incident>(`/incidents/${id}/status`, {
        method: 'POST',
        body: JSON.stringify({ target_status, actor }),
      }),

    assessments: (id: string) =>
      request<AIAssessment[]>(`/incidents/${id}/assessments`),

    triage: (id: string) =>
      request<AIAssessment>(`/incidents/${id}/triage`, { method: 'POST', body: '{}' }),

    reviewTriage: (
      id: string,
      payload: {
        category: string;
        severity: string;
        reviewer?: string;
        justification?: string;
      },
    ) =>
      request<Incident>(`/incidents/${id}/triage/review`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    verify: (id: string, action: string, reviewer: string, justification: string) =>
      request<Incident>(`/incidents/${id}/verification`, {
        method: 'POST',
        body: JSON.stringify({ action, reviewer, justification }),
      }),

    activity: (id: string) => request<ActivityResponse>(`/incidents/${id}/activity`),

    addNote: (id: string, body: string, author?: string) =>
      request<ReviewerNote>(`/incidents/${id}/notes`, {
        method: 'POST',
        body: JSON.stringify({ body, author }),
      }),

    addAction: (
      id: string,
      payload: {
        title: string;
        action_kind?: string;
        owner?: string;
        status?: string;
        due_date?: string;
        evidence?: string;
      },
    ) =>
      request<CorrectiveAction>(`/incidents/${id}/actions`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  },

  modelIntelligence: {
    overview: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return request<ModelOverviewMetrics>(`/model-intelligence/overview${qs}`);
    },
    leaderboard: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return request<LeaderboardRow[]>(`/model-intelligence/leaderboard${qs}`);
    },
    groups: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return request<ModelGroupsResponse>(`/model-intelligence/groups${qs}`);
    },
    detail: (provider: string, model: string, params?: Record<string, string>) => {
      const p = { provider, model, ...params };
      const qs = '?' + new URLSearchParams(p).toString();
      return request<ModelDetail>(`/model-intelligence/detail${qs}`);
    },
    compare: (payload: Record<string, unknown>) =>
      request<{ selected: VersionRow[]; sufficient: boolean }>(
        '/model-intelligence/compare',
        { method: 'POST', body: JSON.stringify(payload) },
      ),
  },

  reports: {
    markdownUrl: (id: string, redact = false) =>
      `${API_BASE}/reports/markdown/${id}?redact_reporter=${redact}`,
    pdfUrl: (id: string, redact = false) =>
      `${API_BASE}/reports/pdf/${id}?redact_reporter=${redact}`,
    csvUrl: (params?: Record<string, string>) => {
      const qs = params ? '?' + new URLSearchParams(params).toString() : '';
      return `${API_BASE}/reports/csv${qs}`;
    },
  },

  settings: {
    get: () => request<SettingsResponse>('/settings'),
    seedDemo: () =>
      request<{ message: string; created: number }>('/settings/seed-demo', { method: 'POST', body: '{}' }),
    resetDemo: () =>
      request<{ message: string; removed: number }>('/settings/demo-data', { method: 'DELETE' }),
  },

  enums: () => request<EnumsResponse>('/meta/enums'),
};

export { ApiError };
export default api;
