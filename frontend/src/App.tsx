import React, { useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const colors = {
  bg: '#080C14',
  surface: '#0D1421',
  surfaceAlt: '#111827',
  border: '#1E2D3D',
  borderLight: '#243447',
  accent: '#3B82F6',
  accentDim: '#1D4ED8',
  green: '#10B981',
  yellow: '#F59E0B',
  red: '#EF4444',
  textPrimary: '#F0F6FF',
  textSecondary: '#8BA3BC',
  textDim: '#4A6480',
};

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    background: colors.bg,
    color: colors.textPrimary,
    fontFamily: "'DM Mono', 'Fira Code', 'Courier New', monospace",
    backgroundImage: `radial-gradient(ellipse at 20% 0%, rgba(59,130,246,0.06) 0%, transparent 60%), radial-gradient(ellipse at 80% 100%, rgba(16,185,129,0.04) 0%, transparent 60%)`,
  },
  header: {
    borderBottom: `1px solid ${colors.border}`,
    padding: '0 48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: '64px',
    background: `rgba(13,20,33,0.95)`,
    backdropFilter: 'blur(12px)',
    position: 'sticky' as const,
    top: 0,
    zIndex: 100,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logoDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: colors.green,
    boxShadow: `0 0 8px ${colors.green}`,
    animation: 'pulse 2s infinite',
  },
  logoText: {
    fontSize: '13px',
    fontWeight: '600',
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
    color: colors.textPrimary,
  },
  logoSub: {
    fontSize: '11px',
    color: colors.textDim,
    letterSpacing: '0.05em',
  },
  badge: {
    fontSize: '10px',
    letterSpacing: '0.12em',
    textTransform: 'uppercase' as const,
    color: colors.accent,
    border: `1px solid ${colors.border}`,
    padding: '4px 10px',
    borderRadius: '2px',
  },
  main: {
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '48px 24px',
  },
  hero: {
    marginBottom: '48px',
  },
  heroLabel: {
    fontSize: '11px',
    letterSpacing: '0.15em',
    textTransform: 'uppercase' as const,
    color: colors.accent,
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  heroTitle: {
    fontSize: '36px',
    fontWeight: '700',
    lineHeight: '1.15',
    marginBottom: '16px',
    color: colors.textPrimary,
    letterSpacing: '-0.02em',
  },
  heroSub: {
    fontSize: '15px',
    color: colors.textSecondary,
    maxWidth: '560px',
    lineHeight: '1.7',
  },
  inputSection: {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: '4px',
    padding: '32px',
    marginBottom: '40px',
    position: 'relative' as const,
    overflow: 'hidden',
  },
  inputSectionAccent: {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    right: 0,
    height: '2px',
    background: `linear-gradient(90deg, ${colors.accent}, ${colors.green})`,
  },
  inputLabel: {
    fontSize: '11px',
    letterSpacing: '0.12em',
    textTransform: 'uppercase' as const,
    color: colors.textDim,
    marginBottom: '16px',
  },
  inputRow: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap' as const,
    alignItems: 'flex-end',
  },
  inputWrapper: {
    flex: 1,
    minWidth: '200px',
  },
  inputFieldLabel: {
    fontSize: '10px',
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
    color: colors.textDim,
    marginBottom: '8px',
    display: 'block',
  },
  input: {
    width: '100%',
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: '2px',
    padding: '11px 14px',
    color: colors.textPrimary,
    fontSize: '13px',
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  button: {
    background: colors.accent,
    color: '#fff',
    border: 'none',
    borderRadius: '2px',
    padding: '12px 32px',
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: 'inherit',
    fontWeight: '600',
    letterSpacing: '0.08em',
    textTransform: 'uppercase' as const,
    transition: 'all 0.2s',
    whiteSpace: 'nowrap' as const,
    height: '42px',
  },
  buttonDisabled: {
    background: colors.border,
    cursor: 'not-allowed',
  },
  grid2: {
    display: 'grid',
    gridTemplateColumns: '280px 1fr',
    gap: '20px',
    marginBottom: '20px',
  },
  card: {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: '4px',
    padding: '24px',
  },
  cardLabel: {
    fontSize: '10px',
    letterSpacing: '0.14em',
    textTransform: 'uppercase' as const,
    color: colors.textDim,
    marginBottom: '20px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  cardLabelDot: {
    width: '4px',
    height: '4px',
    borderRadius: '50%',
    background: colors.accent,
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
  },
  metricItem: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: '2px',
    padding: '14px',
  },
  metricLabel: {
    fontSize: '10px',
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
    color: colors.textDim,
    marginBottom: '8px',
  },
  metricValue: {
    fontSize: '26px',
    fontWeight: '700',
    color: colors.textPrimary,
    lineHeight: 1,
  },
  reportCard: {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderLeft: `3px solid ${colors.accent}`,
    borderRadius: '4px',
    padding: '28px',
    marginBottom: '20px',
  },
  reportText: {
    color: colors.textSecondary,
    lineHeight: '1.85',
    fontSize: '14px',
  },
  feedbackCard: {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: '4px',
    padding: '28px',
    marginTop: '20px',
  },
  feedbackTitle: {
    fontSize: '13px',
    fontWeight: '600',
    letterSpacing: '0.04em',
    color: colors.textPrimary,
    marginBottom: '6px',
  },
  feedbackSub: {
    fontSize: '12px',
    color: colors.textDim,
    marginBottom: '24px',
    lineHeight: '1.6',
  },
  starsRow: {
    display: 'flex',
    gap: '6px',
    marginBottom: '20px',
  },
  starBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '22px',
    padding: '0',
    transition: 'transform 0.1s',
    lineHeight: 1,
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    marginBottom: '12px',
  },
  formField: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
  },
  formLabel: {
    fontSize: '10px',
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
    color: colors.textDim,
  },
  formInput: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: '2px',
    padding: '10px 12px',
    color: colors.textPrimary,
    fontSize: '13px',
    fontFamily: 'inherit',
    outline: 'none',
  },
  textarea: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: '2px',
    padding: '10px 12px',
    color: colors.textPrimary,
    fontSize: '13px',
    fontFamily: 'inherit',
    outline: 'none',
    resize: 'vertical' as const,
    minHeight: '80px',
    width: '100%',
    boxSizing: 'border-box' as const,
    marginBottom: '12px',
  },
  successCard: {
    background: 'rgba(16,185,129,0.06)',
    border: `1px solid rgba(16,185,129,0.2)`,
    borderRadius: '4px',
    padding: '20px',
    textAlign: 'center' as const,
  },
  footer: {
    borderTop: `1px solid ${colors.border}`,
    padding: '20px 48px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '80px',
  },
  footerText: {
    fontSize: '11px',
    color: colors.textDim,
    letterSpacing: '0.06em',
  },
};

function ScoreRing({ score }: { score: number }) {
  const color = score >= 80 ? colors.green : score >= 60 ? colors.yellow : colors.red;
  const label = score >= 80 ? 'HEALTHY' : score >= 60 ? 'AT RISK' : 'CRITICAL';
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '12px 0' }}>
      <div style={{ position: 'relative', width: '140px', height: '140px' }}>
        <svg width="140" height="140" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="70" cy="70" r="54" fill="none" stroke={colors.border} strokeWidth="6" />
          <circle cx="70" cy="70" r="54" fill="none" stroke={color} strokeWidth="6"
            strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round" style={{ transition: 'stroke-dashoffset 1s ease' }} />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: '32px', fontWeight: '700', color, lineHeight: 1 }}>{score}</span>
          <span style={{ fontSize: '11px', color: colors.textDim }}>/100</span>
        </div>
      </div>
      <div style={{ marginTop: '12px', fontSize: '11px', letterSpacing: '0.14em', color, fontWeight: '600' }}>{label}</div>
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

  const submit = async () => {
    await axios.post('http://localhost:8000/review', { owner, repo, rating, comment, name, user_email: userEmail, role });
    setSubmitted(true);
  };

  if (submitted) return (
    <div style={styles.successCard}>
      <div style={{ fontSize: '13px', color: colors.green, fontWeight: '600', marginBottom: '6px' }}>Feedback recorded</div>
      <div style={{ fontSize: '12px', color: colors.textDim }}>Thank you. I would love to connect and hear more about how this can help your team.</div>
    </div>
  );

  return (
    <div style={styles.feedbackCard}>
      <div style={styles.feedbackTitle}>Was this report useful?</div>
      <div style={styles.feedbackSub}>
        If you are an engineering manager or team lead, I would love to hear your thoughts and connect.
      </div>
      <div style={styles.starsRow}>
        {[1,2,3,4,5].map(s => (
          <button key={s} onClick={() => setRating(s)} style={styles.starBtn}>
            <span style={{ opacity: rating >= s ? 1 : 0.2, color: colors.yellow }}>★</span>
          </button>
        ))}
      </div>
      <div style={styles.formGrid}>
        <div style={styles.formField}>
          <label style={styles.formLabel}>Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="Optional" style={styles.formInput} />
        </div>
        <div style={styles.formField}>
          <label style={styles.formLabel}>Email</label>
          <input value={userEmail} onChange={e => setUserEmail(e.target.value)} placeholder="Optional" style={styles.formInput} />
        </div>
      </div>
      <div style={{ ...styles.formField, marginBottom: '12px' }}>
        <label style={styles.formLabel}>Role</label>
        <input value={role} onChange={e => setRole(e.target.value)} placeholder="e.g. Engineering Manager, Tech Lead" style={styles.formInput} />
      </div>
      <textarea value={comment} onChange={e => setComment(e.target.value)}
        placeholder="How could this tool help your team?"
        style={styles.textarea} />
      <button onClick={submit} disabled={rating === 0}
        style={{ ...styles.button, ...(rating === 0 ? styles.buttonDisabled : {}) }}>
        Submit Feedback
      </button>
    </div>
  );
}

export default function App() {
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
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
      setError('Could not connect to server.');
    }
    setLoading(false);
  };

  const commitData = result
    ? Object.entries(result.commit_metrics?.commits_per_author || {}).map(([name, count]) => ({ name, commits: count }))
    : [];

  return (
    <div style={styles.app}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        input:focus { border-color: #3B82F6 !important; }
        input::placeholder { color: #4A6480; }
        textarea::placeholder { color: #4A6480; }
        textarea:focus { border-color: #3B82F6 !important; outline: none; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #080C14; }
        ::-webkit-scrollbar-thumb { background: #1E2D3D; border-radius: 2px; }
      `}</style>

      <header style={styles.header}>
        <div style={styles.logo}>
          <div style={styles.logoDot} />
          <div>
            <div style={styles.logoText}>Dev Productivity Intelligence</div>
            <div style={styles.logoSub}>AI-powered team health analysis</div>
          </div>
        </div>
        <div style={styles.badge}>Beta</div>
      </header>

      <main style={styles.main}>
        <div style={styles.hero}>
          <div style={styles.heroLabel}>
            <span>—</span>
            <span>Team Health Platform</span>
          </div>
          <h1 style={styles.heroTitle}>
            See burnout coming<br />before it costs you.
          </h1>
          <p style={styles.heroSub}>
            Enter any GitHub repository to get an AI-powered weekly health report grounded in your team's own historical incidents.
          </p>
        </div>

        <div style={styles.inputSection}>
          <div style={styles.inputSectionAccent} />
          <div style={styles.inputLabel}>— Analyze repository</div>
          <div style={styles.inputRow}>
            <div style={styles.inputWrapper}>
              <label style={styles.inputFieldLabel}>GitHub Owner</label>
              <input value={owner} onChange={e => setOwner(e.target.value)}
                placeholder="ttabirami12062" style={styles.input} />
            </div>
            <div style={styles.inputWrapper}>
              <label style={styles.inputFieldLabel}>Repository</label>
              <input value={repo} onChange={e => setRepo(e.target.value)}
                placeholder="IPMS" onKeyDown={e => e.key === 'Enter' && analyze()}
                style={styles.input} />
            </div>
            <button onClick={analyze} disabled={loading || !owner || !repo}
              style={{ ...styles.button, ...(loading || !owner || !repo ? styles.buttonDisabled : {}) }}>
              {loading ? 'Analyzing...' : 'Run Analysis'}
            </button>
          </div>
          {error && <div style={{ color: colors.red, fontSize: '12px', marginTop: '12px' }}>{error}</div>}
        </div>

        {result && (
          <>
            <div style={styles.grid2}>
              <div style={styles.card}>
                <div style={styles.cardLabel}><div style={styles.cardLabelDot} />Health Score</div>
                <ScoreRing score={result.health_score} />
              </div>
              <div style={styles.card}>
                <div style={styles.cardLabel}><div style={styles.cardLabelDot} />PR Metrics</div>
                <div style={styles.metricsGrid}>
                  {[
                    { label: 'Total PRs', value: result.pr_metrics?.total_prs ?? 'N/A' },
                    { label: 'Merged', value: result.pr_metrics?.merged_prs ?? 'N/A' },
                    { label: 'Open', value: result.pr_metrics?.open_prs ?? 'N/A' },
                    { label: 'Avg Review', value: result.pr_metrics?.avg_review_time_hours ? `${result.pr_metrics.avg_review_time_hours}h` : 'N/A' },
                  ].map(({ label, value }) => (
                    <div key={label} style={styles.metricItem}>
                      <div style={styles.metricLabel}>{label}</div>
                      <div style={styles.metricValue}>{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {commitData.length > 0 && (
              <div style={{ ...styles.card, marginBottom: '20px' }}>
                <div style={styles.cardLabel}><div style={styles.cardLabelDot} />Commit Distribution</div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={commitData} barSize={28}>
                    <CartesianGrid strokeDasharray="2 4" stroke={colors.border} vertical={false} />
                    <XAxis dataKey="name" stroke={colors.textDim} fontSize={11} fontFamily="inherit" tickLine={false} axisLine={false} />
                    <YAxis stroke={colors.textDim} fontSize={11} fontFamily="inherit" tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: '2px', fontSize: '12px', fontFamily: 'inherit' }} cursor={{ fill: 'rgba(59,130,246,0.05)' }} />
                    <Bar dataKey="commits" fill={colors.accent} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <div style={styles.reportCard}>
              <div style={styles.cardLabel}><div style={styles.cardLabelDot} />AI Weekly Health Report</div>
              <div style={styles.reportText} dangerouslySetInnerHTML={{ __html: result.report.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>') }} />
            </div>

            <ReviewSection owner={result.owner} repo={result.repo} />
          </>
        )}
      </main>

      <footer style={styles.footer}>
        <div style={styles.footerText}>Dev Productivity Intelligence — Built by Abirami Thiyagarajan</div>
        <div style={styles.footerText}>github.com/ttabirami12062</div>
      </footer>
    </div>
  );
}