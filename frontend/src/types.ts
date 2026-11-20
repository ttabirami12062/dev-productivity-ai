export type Status = 'healthy' | 'watch' | 'at_risk' | 'quiet';
export type FindingKind = 'risk' | 'action' | 'positive';

export interface Week {
  week_start: string;
  label: string;
  merged: number;
  median_hours: number | null;
}

export interface Metrics {
  window: { since: string; until: string; days: number };
  people: number;
  solo: boolean;
  quiet: boolean;
  uses_prs: boolean;
  prs: {
    total: number;
    merged: number;
    open: number;
    stale_open: number;
    closed_unmerged: number;
    median_merge_hours: number | null;
    weekly: Week[];
  };
  reviews: {
    total: number;
    reviewed_prs: number;
    per_reviewer: Record<string, number>;
    top_reviewer: string | null;
    top_share: number;
  };
  commits: {
    total: number;
    per_author: Record<string, number>;
    top_author: string | null;
    top_share: number;
  };
}

export interface Finding {
  kind: FindingKind;
  title: string;
  detail: string;
  sources: number[];
}

export interface Source {
  id: number;
  title: string;
  match: number;
}

export interface Analysis {
  success: true;
  owner: string;
  repo: string;
  health_score: number;
  status: Status;
  signals: string[];
  metrics: Metrics;
  report: { headline: string; highlight: string; summary: string; findings: Finding[] };
  sources: Source[];
  generated_seconds: number;
  cached?: boolean;
}

export type AnalyzeResponse = Analysis | { success: false; error: string };
