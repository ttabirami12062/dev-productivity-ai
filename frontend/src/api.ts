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

export async function analyzeRepo(owner: string, repo: string): Promise<AnalyzeResponse> {
  try {
    // The free server can take close to a minute to wake up, so allow plenty of time.
    const res = await axios.post<AnalyzeResponse>(`${API_URL}/analyze`, { owner, repo }, { timeout: 150000 });
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
}): Promise<boolean> {
  try {
    await axios.post(`${API_URL}/review`, body, { timeout: 30000 });
    return true;
  } catch {
    return false;
  }
}
