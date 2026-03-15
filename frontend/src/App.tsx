import React, { useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Metrics {
  total_prs: number;
  merged_prs: number;
  open_prs: number;
  avg_review_time_hours: number;
}

interface CommitMetrics {
  total_commits: number;
  most_active_author: string;
  commits_per_author: Record<string, number>;
}

interface AnalysisResult {
  success: boolean;
  owner: string;
  repo: string;
  health_score: number;
  pr_metrics: Metrics;
  commit_metrics: CommitMetrics;
  report: string;
  error?: string;
}

function HealthScoreCircle({ score }: { score: number }) {
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ textAlign: 'center', padding: '20px' }}>
      <div style={{
        width: '140px', height: '140px', borderRadius: '50%',
        border: `8px solid ${color}`, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', margin: '0 auto',
        backgroundColor: '#1e1e2e'
      }}>
        <span style={{ fontSize: '36px', fontWeight: 'bold', color }}>{score}</span>
        <span style={{ fontSize: '12px', color: '#888' }}>/ 100</span>
      </div>
      <p style={{ color, marginTop: '10px', fontWeight: 'bold' }}>
        {score >= 80 ? 'Healthy' : score >= 60 ? 'At Risk' : 'Critical'}
      </p>
    </div>
  );
}

function ReviewSection({ owner, repo }: { owner: string; repo: string }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [name, setName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [role, setRole] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const submitReview = async () => {
    await axios.post('http://localhost:8000/review', {
      owner, repo, rating, comment, name, user_email: userEmail, role
    });
    setSubmitted(true);
  };

  if (submitted) return (
    <div style={{ background: '#1e2a1e', border: '1px solid #22c55e', borderRadius: '12px', padding: '24px', textAlign: 'center' }}>
      <p style={{ color: '#22c55e', fontSize: '18px', margin: '0 0 8px' }}>Thank you for your feedback!</p>
      <p style={{ color: '#888', fontSize: '14px', margin: 0 }}>Your response has been recorded. I would love to connect and hear more about how this can help your team.</p>
    </div>
  );

  return (
    <div style={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '12px', padding: '24px', marginTop: '24px' }}>
      <h3 style={{ color: '#fff', marginBottom: '4px' }}>Was this report helpful?</h3>
      <p style={{ color: '#888', fontSize: '13px', marginBottom: '20px' }}>
        If you are an engineering manager or team lead, I would love to hear how this tool could help your team. Feel free to leave your contact details and I will reach out personally.
      </p>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        {[1, 2, 3, 4, 5].map(star => (
          <button key={star} onClick={() => setRating(star)}
            style={{
              fontSize: '28px', background: 'none', border: 'none', cursor: 'pointer',
              opacity: rating >= star ? 1 : 0.3, transition: 'opacity 0.2s', color: '#f59e0b'
            }}>★</button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
        <input value={name} onChange={e => setName(e.target.value)}
          placeholder="Your name (optional)"
          style={{ background: '#0f0f1a', border: '1px solid #333', borderRadius: '8px', padding: '10px 14px', color: '#fff', fontSize: '14px' }} />
        <input value={userEmail} onChange={e => setUserEmail(e.target.value)}
          placeholder="Your email (optional)"
          style={{ background: '#0f0f1a', border: '1px solid #333', borderRadius: '8px', padding: '10px 14px', color: '#fff', fontSize: '14px' }} />
      </div>

      <input value={role} onChange={e => setRole(e.target.value)}
        placeholder="Your role (e.g. Engineering Manager, Tech Lead)"
        style={{ width: '100%', background: '#0f0f1a', border: '1px solid #333', borderRadius: '8px', padding: '10px 14px', color: '#fff', fontSize: '14px', marginBottom: '12px', boxSizing: 'border-box' }} />

      <textarea value={comment} onChange={e => setComment(e.target.value)}
        placeholder="How could this tool help your team? Any suggestions?"
        style={{ width: '100%', minHeight: '80px', background: '#0f0f1a', border: '1px solid #333', borderRadius: '8px', padding: '12px', color: '#fff', fontSize: '14px', resize: 'vertical', boxSizing: 'border-box', marginBottom: '12px' }} />

      <button onClick={submitReview} disabled={rating === 0}
        style={{
          background: rating === 0 ? '#333' : '#1A56DB', color: '#fff', border: 'none',
          borderRadius: '8px', padding: '10px 24px', cursor: rating === 0 ? 'not-allowed' : 'pointer',
          fontSize: '14px', fontWeight: 'bold'
        }}>
        Submit Feedback
      </button>
    </div>
  );
}

export default function App() {
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState('');

  const analyze = async () => {
    if (!owner || !repo) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await axios.post('http://localhost:8000/analyze', { owner, repo });
      if (res.data.success) setResult(res.data);
      else setError(res.data.error || 'Analysis failed');
    } catch {
      setError('Could not connect to server. Make sure the backend is running.');
    }
    setLoading(false);
  };

  const commitData = result ? Object.entries(result.commit_metrics.commits_per_author || {}).map(([name, count]) => ({ name, commits: count })) : [];

  return (
    <div style={{ minHeight: '100vh', background: '#0f0f1a', color: '#fff', fontFamily: 'Inter, sans-serif' }}>

      <div style={{ background: '#1a1a2e', borderBottom: '1px solid #333', padding: '20px 40px' }}>
        <h1 style={{ margin: 0, fontSize: '20px', fontWeight: 'bold', color: '#fff' }}>Dev Productivity Intelligence</h1>
        <p style={{ margin: 0, fontSize: '12px', color: '#888' }}>AI-powered team health analysis</p>
      </div>

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '40px 20px' }}>

        <div style={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '16px', padding: '32px', marginBottom: '32px' }}>
          <h2 style={{ margin: '0 0 8px', fontSize: '24px' }}>Analyze Your Team Health</h2>
          <p style={{ color: '#888', margin: '0 0 24px', fontSize: '14px' }}>Enter a GitHub repository to get an AI-powered weekly health report</p>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <input value={owner} onChange={e => setOwner(e.target.value)}
              placeholder="GitHub Owner (e.g. ttabirami12062)"
              style={{ flex: 1, minWidth: '200px', background: '#0f0f1a', border: '1px solid #333', borderRadius: '8px', padding: '12px 16px', color: '#fff', fontSize: '14px' }} />
            <input value={repo} onChange={e => setRepo(e.target.value)}
              placeholder="Repository (e.g. IPMS)"
              onKeyDown={e => e.key === 'Enter' && analyze()}
              style={{ flex: 1, minWidth: '200px', background: '#0f0f1a', border: '1px solid #333', borderRadius: '8px', padding: '12px 16px', color: '#fff', fontSize: '14px' }} />
            <button onClick={analyze} disabled={loading || !owner || !repo}
              style={{
                background: loading ? '#333' : '#1A56DB', color: '#fff', border: 'none',
                borderRadius: '8px', padding: '12px 28px', cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '14px', fontWeight: 'bold', whiteSpace: 'nowrap'
              }}>
              {loading ? 'Analyzing...' : 'Analyze Team'}
            </button>
          </div>
          {error && <p style={{ color: '#ef4444', marginTop: '12px', fontSize: '14px' }}>{error}</p>}
        </div>

        {result && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px', marginBottom: '24px' }}>
              <div style={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '16px', padding: '24px' }}>
                <h3 style={{ margin: '0 0 16px', color: '#888', fontSize: '14px', textTransform: 'uppercase' }}>Health Score</h3>
                <HealthScoreCircle score={result.health_score} />
              </div>
              <div style={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '16px', padding: '24px' }}>
                <h3 style={{ margin: '0 0 16px', color: '#888', fontSize: '14px', textTransform: 'uppercase' }}>PR Metrics</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  {[
                    { label: 'Total PRs', value: result.pr_metrics.total_prs ?? 'N/A' },
                    { label: 'Merged PRs', value: result.pr_metrics.merged_prs ?? 'N/A' },
                    { label: 'Open PRs', value: result.pr_metrics.open_prs ?? 'N/A' },
                    { label: 'Avg Review Time', value: result.pr_metrics.avg_review_time_hours ? `${result.pr_metrics.avg_review_time_hours}h` : 'N/A' },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ background: '#0f0f1a', borderRadius: '8px', padding: '16px' }}>
                      <p style={{ margin: 0, color: '#888', fontSize: '12px' }}>{label}</p>
                      <p style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 'bold', color: '#fff' }}>{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {commitData.length > 0 && (
              <div style={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '16px', padding: '24px', marginBottom: '24px' }}>
                <h3 style={{ margin: '0 0 20px', color: '#888', fontSize: '14px', textTransform: 'uppercase' }}>Commits Per Developer</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={commitData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="name" stroke="#888" fontSize={12} />
                    <YAxis stroke="#888" fontSize={12} />
                    <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #333', borderRadius: '8px' }} />
                    <Bar dataKey="commits" fill="#1A56DB" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div style={{ background: '#1a1a2e', border: '1px solid #1A56DB', borderRadius: '16px', padding: '24px', marginBottom: '24px' }}>
              <h3 style={{ margin: '0 0 16px', color: '#1A56DB', fontSize: '14px', textTransform: 'uppercase' }}>AI Weekly Health Report</h3>
              <div style={{ color: '#ddd', lineHeight: '1.8', fontSize: '15px', whiteSpace: 'pre-wrap' }}>
                {result.report}
              </div>
            </div>

            <ReviewSection owner={result.owner} repo={result.repo} />
          </>
        )}
      </div>
    </div>
  );
}