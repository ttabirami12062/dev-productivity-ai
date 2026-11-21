import axios from 'axios';
import { AnalyzeResponse } from './types';

// Set REACT_APP_API_URL in Vercel to point at a different backend; falls back to the Render one.
export const API_URL = process.env.REACT_APP_API_URL || 'https://dev-productivity-ai.onrender.com';

// Accepts "owner/name", "github.com/owner/name" or a full GitHub link.
export function parseRepo(input: string): { owner: string; repo: string } | null {
  const cleaned = input
    .trim()
    .replace(/^https?:\/\//, '')
    .replace(/^(www\.)?github\.com\//, '')
    .replace(/\.git$/, '')
    .replace(/\/+$/, '');
  const [owner, repo] = cleaned.split('/');
  const ok = /^[A-Za-z0-9._-]{1,100}$/;
  return owner && repo && ok.test(owner) && ok.test(repo) ? { owner, repo } : null;
}

// The browser's own time zone, e.g. "America/Chicago", so weeks and dates match GitHub for this visitor.
export const timeZone = (() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
})();

export async function analyzeRepo(owner: string, repo: string, team = ''): Promise<AnalyzeResponse> {
  try {
    // The free server can take close to a minute to wake up, so allow plenty of time.
    const res = await axios.post<AnalyzeResponse>(`${API_URL}/analyze`, { owner, repo, timezone: timeZone, team }, { timeout: 150000 });
    return res.data;
  } catch {
    return { success: false, error: "We couldn't reach the server. Check your connection and try again." };
  }
}

export async function sendFeedback(body: {
  owner: string;
  repo: string;
  rating: number;
  comment: string;
  name: string;
  user_email: string;
  role: string;
  trace_id?: string | null;
}): Promise<boolean> {
  try {
    await axios.post(`${API_URL}/review`, body, { timeout: 30000 });
    return true;
  } catch {
    return false;
  }
}

// ── Team spaces ──
// A team is a random id in the page link (?team=...). Its documents replace the samples in reports.

export interface TeamDoc {
  id: string;
  title: string;
  added: string;
  chunks: number;
}

type Result<T> = ({ success: true } & T) | { success: false; error: string };
const offline = { success: false as const, error: "We couldn't reach the server. Check your connection and try again." };

export async function createTeam(): Promise<Result<{ team: string }>> {
  try {
    return (await axios.post(`${API_URL}/teams`, {}, { timeout: 90000 })).data;
  } catch {
    return offline;
  }
}

export async function listTeamDocs(team: string): Promise<Result<{ documents: TeamDoc[] }>> {
  try {
    return (await axios.get(`${API_URL}/teams/${team}/documents`, { timeout: 90000 })).data;
  } catch {
    return offline;
  }
}

export async function addTeamDoc(team: string, input: { title: string; text: string; file: File | null }): Promise<Result<{ document: TeamDoc }>> {
  const form = new FormData();
  form.append('title', input.title);
  form.append('text', input.text);
  if (input.file) form.append('file', input.file);
  try {
    return (await axios.post(`${API_URL}/teams/${team}/documents`, form, { timeout: 120000 })).data;
  } catch {
    return offline;
  }
}

export async function removeTeamDoc(team: string, docId: string): Promise<Result<{}>> {
  try {
    return (await axios.delete(`${API_URL}/teams/${team}/documents/${docId}`, { timeout: 60000 })).data;
  } catch {
    return offline;
  }
}

// ── History (daily snapshots of tracked repos) ──

export interface Snapshot {
  day: string;
  health_score: number;
  status: string;
  median_merge_hours: number | null;
  latest_week_hours: number | null;
  top_review_share: number | null;
  stale_open_prs: number;
}

export interface Change {
  label: string;
  text: string;
  worse: boolean;
}

export async function getHistory(owner: string, repo: string): Promise<Result<{ enabled: boolean; tracked: boolean; snapshots: Snapshot[]; changes: Change[] }>> {
  try {
    return (await axios.get(`${API_URL}/history/${owner}/${repo}`, { timeout: 60000 })).data;
  } catch {
    return offline;
  }
}

export async function trackRepo(owner: string, repo: string): Promise<Result<{}>> {
  try {
    return (await axios.post(`${API_URL}/track`, { owner, repo }, { timeout: 120000 })).data;
  } catch {
    return offline;
  }
}
