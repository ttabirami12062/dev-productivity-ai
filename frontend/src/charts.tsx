import { Status, Week } from './types';

export const COLORS = {
  ink2: '#4B5A54',
  ink3: '#7F8D87',
  grid: '#EEF1ED',
  calm: '#9DB8AE',
  good: '#1E8A4C',
  warn: '#C27A00',
  bad: '#C8372D',
};

export const statusColor = (s: Status) =>
  s === 'healthy' ? COLORS.good : s === 'watch' ? COLORS.warn : s === 'quiet' ? COLORS.ink3 : COLORS.bad;

export function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null;
  const w = 88, h = 26, p = 3;
  const min = Math.min(...values), max = Math.max(...values);
  const pts = values.map((v, i) => [p + (i * (w - 2 * p)) / (values.length - 1), h - p - ((v - min) / (max - min || 1)) * (h - 2 * p)]);
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const [lx, ly] = pts[pts.length - 1];
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <path d={`${line} L${lx} ${h} L${p} ${h}Z`} fill={color} opacity={0.12} />
      <path d={line} fill="none" stroke={color} strokeWidth={1.8} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r={2.8} fill={color} />
    </svg>
  );
}

// A heartbeat trace whose spikes grow as the score drops, so the mood reads before any number.
export function Pulse({ score, status }: { score: number; status: Status }) {
  const strain = status === 'quiet' ? 0.05 : Math.max(0.15, (100 - score) / 100);
  const beats = [180, 360, 540, 720, 900];
  let d = 'M0 40';
  beats.forEach((x, i) => {
    const amp = (8 + i * 6) * strain * 1.6;
    d += ` H${x} l12 ${-amp} l14 ${amp * 1.7} l12 ${-amp * 0.7}`;
  });
  d += ' H1120';
  return (
    <div className="pulse" aria-hidden="true">
      <svg viewBox="0 0 1120 64" preserveAspectRatio="none">
        <line x1="0" y1="40" x2="1120" y2="40" stroke="#DCE1DC" strokeWidth="1" />
        <path className="trace" d={d} fill="none" stroke={statusColor(status)} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
    </div>
  );
}

export function MergeChart({ weeks, target }: { weeks: Week[]; target: number }) {
  const W = 540, H = 236, L = 38, R = 10, T = 16, B = 42;
  const highest = Math.max(target, ...weeks.map((w) => w.median_hours ?? 0));
  // Pick a round step that gives at most about six grid lines, even for month-long waits.
  const step = [10, 20, 50, 100, 200, 500, 1000].find((st) => (highest * 1.1) / st <= 6) ?? 2000;
  const max = Math.ceil((highest * 1.1) / step) * step;
  const y = (v: number) => T + (H - T - B) * (1 - v / max);
  const bw = (W - L - R) / weeks.length;
  const ticks = Array.from({ length: max / step + 1 }, (_, i) => i * step);
  let lastWithData = -1;
  weeks.forEach((w, i) => { if (w.median_hours !== null) lastWithData = i; });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Median hours from open to merge for each of the last ${weeks.length} weeks, with a ${target} hour target`}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke={COLORS.grid} />
          <text x={L - 6} y={y(t) + 4} textAnchor="end">{t}h</text>
        </g>
      ))}
      {weeks.map((w, i) => {
        const x = L + i * bw + bw * 0.2, bwid = bw * 0.6;
        const v = w.median_hours;
        return (
          <g key={w.week_start}>
            {v === null ? (
              <text x={x + bwid / 2} y={y(0) - 6} textAnchor="middle">none</text>
            ) : (
              <rect x={x} y={y(v)} width={bwid} height={Math.max(1, y(0) - y(v))} rx={3} fill={v > target ? COLORS.bad : COLORS.calm} />
            )}
            {v !== null && i === lastWithData && (
              <text x={x + bwid / 2} y={y(v) - 6} textAnchor="middle" style={{ fill: v > target ? COLORS.bad : COLORS.ink2, fontWeight: 500 }}>{v}h</text>
            )}
            <text x={x + bwid / 2} y={H - 24} textAnchor="middle">{w.label.replace('-', '\u2013')}</text>
            <text x={x + bwid / 2} y={H - 9} textAnchor="middle" style={{ fill: COLORS.ink2 }}>{w.merged === 1 ? '1 merged' : `${w.merged} merged`}</text>
          </g>
        );
      })}
      <line x1={L} x2={W - R} y1={y(target)} y2={y(target)} stroke={COLORS.ink2} strokeWidth={1.5} strokeDasharray="5 4" />
      <text x={W - R} y={y(target) - 6} textAnchor="end" style={{ fill: COLORS.ink2 }}>{target}h target</text>
    </svg>
  );
}

export function LoadBars({ counts, limit }: { counts: Record<string, number>; limit: number }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const entries = Object.entries(counts);
  const shown = entries.slice(0, 5);
  const rest = entries.slice(5).reduce((a, [, n]) => a + n, 0);
  if (rest) shown.push([`${entries.length - 5} others`, rest]);
  return (
    <div className="load">
      {shown.map(([name, n]) => {
        const pct = Math.round((n / total) * 100);
        return (
          <div className="load-row" key={name}>
            <span className="load-name" title={name}>{name}</span>
            <span className="load-track">
              <span className={`load-fill${pct > limit ? ' hot' : ''}`} style={{ width: `${pct}%` }} />
              <span className="load-limit" style={{ left: `${limit}%` }} />
            </span>
            <span className="load-pct">{pct}%</span>
          </div>
        );
      })}
    </div>
  );
}

export function BrandMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <rect width="26" height="26" rx="7" fill="#0E6B57" />
      <path d="M4 14h4l2.5-6 4 11 2.5-5H22" fill="none" stroke="#FFE34D" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export const Cite = ({ n, href }: { n: number | string; href?: string }) =>
  href ? <a className="cite" href={href}>{n}</a> : <span className="cite">{n}</span>;

