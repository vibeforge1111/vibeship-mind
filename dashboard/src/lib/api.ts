/**
 * Mind API Client
 * Connects to the Mind HTTP API
 */

const API_BASE = 'http://127.0.0.1:8765';

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  stack: string[];
  repo_path: string | null;
  current_goal: string | null;
  blocked_by: string[];
  open_threads: string[];
  last_session_id: string | null;
  last_session_date: string | null;
  last_session_summary: string | null;
  last_session_mood: string | null;
  last_session_next_step: string | null;
  created_at: string;
  updated_at: string;
}

export interface Decision {
  id: string;
  project_id: string;
  title: string;
  description: string;
  context: string;
  reasoning: string;
  alternatives: Array<{ option: string; rejected_because: string }>;
  confidence: number;
  trigger_phrases: string[];
  revisit_if: string | null;
  status: string;
  superseded_by: string | null;
  related_issues: string[];
  related_edges: string[];
  related_decisions: string[];
  created_at: string;
  updated_at: string;
}

export interface Issue {
  id: string;
  project_id: string;
  title: string;
  description: string;
  symptoms: string[];
  current_theory: string | null;
  attempts: Array<{ what: string; result: string; learned: string }>;
  severity: string;
  status: string;
  blocked_by: string | null;
  resolution: string | null;
  trigger_phrases: string[];
  related_decisions: string[];
  related_edges: string[];
  created_at: string;
  updated_at: string;
}

export interface SharpEdge {
  id: string;
  project_id: string | null;
  title: string;
  description: string;
  detection_patterns: Array<{ type: string; pattern: string; description: string }>;
  trigger_phrases: string[];
  symptoms: string[];
  workaround: string;
  root_cause: string | null;
  proper_fix: string | null;
  discovered_at: string;
  related_decisions: string[];
  related_issues: string[];
}

export interface Episode {
  id: string;
  project_id: string;
  session_id: string;
  title: string;
  summary: string;
  the_journey: string | null;
  outcome: string | null;
  mood: string | null;
  lessons_learned: string[];
  artifacts_created: string[];
  significance_markers: string[];
  custom_title: boolean;
  created_at: string;
}

export interface Session {
  id: string;
  project_id: string;
  started_at: string;
  ended_at: string | null;
  summary: string | null;
  mood: string | null;
  progress: string[];
  still_open: string[];
  next_steps: string[];
  decisions_made: string[];
  issues_resolved: string[];
  issues_encountered: string[];
  edges_triggered: string[];
}

export interface User {
  id: string;
  total_sessions: number;
  first_session: string | null;
  last_session: string | null;
  preferences: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Stats {
  projects: number;
  decisions: number;
  issues: number;
  edges: number;
  episodes: number;
}

export interface StatusResponse {
  status: string;
  version: string;
  timestamp: string;
  stats: Stats;
}

export interface ListResponse<T> {
  items: T[];
  count: number;
  has_more: boolean;
}

export interface SearchResults {
  query: string;
  project_id: string;
  decisions: Decision[];
  issues: Issue[];
  edges: SharpEdge[];
  episodes: Episode[];
  total: number;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Unknown error' }));
    throw new ApiError(response.status, error.message || `HTTP ${response.status}`);
  }

  return response.json();
}

// Status & Stats
export const getStatus = () => request<StatusResponse>('/status');
export const getUser = () => request<User>('/user');

// Projects
export const getProjects = () => request<ListResponse<Project>>('/projects');
export const getProject = (id: string) => request<Project>(`/projects/${id}`);
export const createProject = (data: { name: string; description?: string }) =>
  request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) });
export const deleteProject = (id: string) =>
  request<void>(`/projects/${id}`, { method: 'DELETE' });

// Decisions
export const getDecisions = (projectId: string) =>
  request<ListResponse<Decision>>(`/decisions/${projectId}`);
export const getDecision = (projectId: string, id: string) =>
  request<Decision>(`/decisions/${projectId}/${id}`);

// Issues
export const getIssues = (projectId: string, openOnly = false) =>
  request<ListResponse<Issue>>(`/issues/${projectId}${openOnly ? '?open_only=true' : ''}`);
export const getIssue = (projectId: string, id: string) =>
  request<Issue>(`/issues/${projectId}/${id}`);

// Edges
export const getEdges = (projectId?: string, globalOnly = false) => {
  const params = new URLSearchParams();
  if (projectId) params.set('project_id', projectId);
  if (globalOnly) params.set('global_only', 'true');
  const query = params.toString();
  return request<ListResponse<SharpEdge>>(`/edges${query ? `?${query}` : ''}`);
};
export const getEdge = (id: string) => request<SharpEdge>(`/edges/${id}`);

// Episodes
export const getEpisodes = (projectId: string) =>
  request<ListResponse<Episode>>(`/episodes/${projectId}`);
export const getEpisode = (projectId: string, id: string) =>
  request<Episode>(`/episodes/${projectId}/${id}`);

// Sessions
export const getSessions = (projectId: string) =>
  request<ListResponse<Session>>(`/sessions/${projectId}`);
export const getActiveSession = (projectId: string) =>
  request<Session | null>(`/sessions/${projectId}/active`);

// Search
export const search = (query: string, projectId: string) =>
  request<SearchResults>(`/search?q=${encodeURIComponent(query)}&project_id=${projectId}`);

// Export
export const exportData = (projectId?: string, includeSessions = false) => {
  const params = new URLSearchParams();
  if (projectId) params.set('project_id', projectId);
  if (includeSessions) params.set('include_sessions', 'true');
  const query = params.toString();
  return request<unknown>(`/export${query ? `?${query}` : ''}`);
};

// Utility functions
export function formatRelativeTime(date: string | null): string {
  if (!date) return 'never';

  const now = new Date();
  const then = new Date(date);
  const diffMs = now.getTime() - then.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutes = Math.floor(diffMs / (1000 * 60));

  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return `${Math.floor(diffDays / 30)} months ago`;
}

export function formatRecencyText(lastSession: string | null): string {
  if (!lastSession) return 'First session together';

  const now = new Date();
  const then = new Date(lastSession);
  const diffMs = now.getTime() - then.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHours < 1) return 'Last together just now';
  if (diffHours < 24) return `Last together ${diffHours} hours ago`;
  if (diffDays === 0) return 'Last together today';
  if (diffDays === 1) return 'Last together yesterday';
  if (diffDays < 7) return `Last together ${diffDays} days ago`;
  if (diffDays < 14) return 'Last together last week';
  return `Last together ${Math.floor(diffDays / 7)} weeks ago`;
}

export function formatDuration(startDate: string, endDate?: string | null): string {
  const start = new Date(startDate);
  const end = endDate ? new Date(endDate) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));

  if (diffMinutes < 60) return `${diffMinutes} min`;
  const hours = Math.floor(diffMinutes / 60);
  const mins = diffMinutes % 60;
  if (mins === 0) return `${hours} hr`;
  return `${hours}.${Math.round(mins / 6)} hrs`;
}

export function getCtaText(user: User | null, hasActiveSession: boolean): string {
  if (!user || user.total_sessions === 0) return 'Start First Session';
  if (hasActiveSession) return 'Return to Session';

  if (user.last_session) {
    const diffDays = Math.floor(
      (Date.now() - new Date(user.last_session).getTime()) / (1000 * 60 * 60 * 24)
    );
    if (diffDays >= 14) return 'Pick Up Where We Left Off';
  }

  return 'Continue Session';
}
