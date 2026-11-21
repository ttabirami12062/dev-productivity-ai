import { useCallback, useEffect, useState } from 'react';
import { Change, getHistory, Snapshot, trackRepo } from './api';
import { COLORS } from './charts';

const fmt = (d: string) => new Date(`${d}T00:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });

function ScoreLine({ points }: { points: Snapshot[] }) {
  const W = 540, H = 200, L = 34, R = 26, T = 14, B = 26;
  const x = (i: number) => L + (points.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (points.length - 1));
  const y = (v: number) => T + (H - T - B) * (1 - v / 100);
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(p.health_score).toFixed(1)}`).join(' ');
  const last = points[points.length - 1];
  // Label roughly five dates so the axis never crowds.
  const every = Math.max(1, Math.ceil(points.length / 5));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Health score over ${points.length} days, now ${last.health_score}`}>
      {[0, 60, 80, 100].map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke={t === 60 || t === 80 ? '#DCE1DC' : COLORS.grid} strokeDasharray={t === 60 || t === 80 ? '4 4' : undefined} />
          <text x={L - 6} y={y(t) + 4} textAnchor="end">{t}</text>
        </g>
      ))}
      <path d={`${line} L${x(points.length - 1)} ${y(0)} L${x(0)} ${y(0)}Z`} fill="#0E6B57" opacity={0.08} />
      <path d={line} fill="none" stroke="#0E6B57" strokeWidth={2.2} strokeLinejoin="round" strokeLinecap="round" />
      {points.map((p, i) => (
        <circle key={p.day} cx={x(i)} cy={y(p.health_score)} r={i === points.length - 1 ? 4 : 2.5} fill={i === points.length - 1 ? '#0E6B57' : '#FFFFFF'} stroke="#0E6B57" strokeWidth={1.5} />
      ))}
      {points.map((p, i) => (i % every === 0 || i === points.length - 1) && (
        // The last label ends at its point so it never runs off the right edge.
        <text key={`t${p.day}`} x={x(i)} y={H - 8} textAnchor={i === points.length - 1 ? 'end' : 'middle'}>{fmt(p.day)}</text>
      ))}
    </svg>
  );
}

export default function Trends({ owner, repo }: { owner: string; repo: string }) {
  const [state, setState] = useState<{ enabled: boolean; tracked: boolean; snapshots: Snapshot[]; changes: Change[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const res = await getHistory(owner, repo);
    if (res.success) setState(res);
  }, [owner, repo]);

  useEffect(() => { load(); }, [load]);

  if (!state || !state.enabled) return null;

  const track = async () => {
    setBusy(true);
    setError('');
    const res = await trackRepo(owner, repo);
    setBusy(false);
    if (res.success) load();
    else setError(res.error);
  };

  const { snapshots, changes } = state;
  return (
    <>
      <h2 className="section-title">Trend over time</h2>
      {!state.tracked ? (
        <div className="panel trend-empty">
          <p>
            Track this project and its numbers are saved every night, so you can see whether things are getting better or worse over the
            coming weeks and months. It's free and uses no AI.
          </p>
          <button type="button" className="btn" onClick={track} disabled={busy}>{busy ? 'Starting...' : 'Track this project'}</button>
          {error && <p className="error">{error}</p>}
        </div>
      ) : snapshots.length < 2 ? (
        <div className="panel trend-empty">
          <p>
            Tracking started on {snapshots[0] ? fmt(snapshots[0].day) : 'today'}. A new point is saved every night, and the trend line appears
            from tomorrow. Bookmark this page and come back in a few days.
          </p>
        </div>
      ) : (
        <div className="evidence">
          <div className="panel chart">
            <h3>Health score, day by day</h3>
            <p className="hint">One point per night since tracking started. Dashed lines mark 80 (healthy) and 60 (at risk).</p>
            <ScoreLine points={snapshots} />
          </div>
          <div className="panel">
            <h3>Compared with before</h3>
            {changes.length ? (
              <ul className="changes">
                {changes.map((c) => (
                  <li key={c.label} className={c.worse ? 'worse' : 'better'}>{c.text}</li>
                ))}
              </ul>
            ) : (
              <p className="empty">Nothing has changed since tracking started.</p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
