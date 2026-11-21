import { Analysis, FindingKind } from './types';
import { COLORS, Cite, LoadBars, MergeChart, Pulse, Sparkline, statusColor } from './charts';

// Kept in step with MERGE_TARGET_HOURS and REVIEW_SHARE_LIMIT in src/metrics.py.
const MERGE_TARGET = 24;
const REVIEW_LIMIT = 50;

const STATUS_LABEL = { healthy: 'Healthy', watch: 'Worth watching', at_risk: 'At risk', quiet: 'Too little activity' };
const KIND_LABEL: Record<FindingKind, string> = { risk: 'Risk', action: 'Do this week', positive: 'Going well' };

const fmtDate = (iso: string) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const plural = (n: number, word: string, capped = false) => `${n}${capped ? '+' : ''} ${word}${n === 1 && !capped ? '' : 's'}`;
// Long waits read better in days: 726 hours is "30 days".
const wait = (h: number) => (h < 48 ? { value: `${h}`, unit: 'h' } : { value: `${h / 24 < 10 ? (h / 24).toFixed(1).replace('.0', '') : Math.round(h / 24)}`, unit: ' days' });

function Headline({ text, highlight }: { text: string; highlight: string }) {
  const at = highlight ? text.indexOf(highlight) : -1;
  if (at < 0) return <h1>{text}</h1>;
  return (
    <h1>
      {text.slice(0, at)}
      <mark>{highlight}</mark>
      {text.slice(at + highlight.length)}
    </h1>
  );
}

export default function Dashboard({ data }: { data: Analysis }) {
  const { metrics: m, report, sources } = data;
  const color = statusColor(data.status);
  // Source 0 is the GitHub data itself; show it after the history documents.
  const githubNum = sources.length + 1;
  const citeNum = (id: number) => (id === 0 ? githubNum : id);

  const weekly = m.prs.weekly.map((w) => w.median_hours).filter((v): v is number => v !== null);
  const mergeChange = weekly.length >= 2 ? Math.round(weekly[weekly.length - 1] - weekly[0]) : null;
  const reviewShareBad = !m.solo && m.reviews.total >= 5 && m.reviews.top_share > REVIEW_LIMIT;

  return (
    <>
      <section className="verdict">
        <div className="verdict-text">
          <p className="eyebrow">
            {data.owner}/{data.repo} &middot; {fmtDate(m.window.since)} to {fmtDate(m.window.until)} &middot; {m.window.timezone.replace(/_/g, ' ')}
          </p>
          <Headline text={report.headline} highlight={report.highlight} />
          <p className="summary">{report.summary}</p>
        </div>
        <div className="score" aria-label={`Health score ${data.health_score} out of 100, ${STATUS_LABEL[data.status]}`}>
          <div className="score-num" style={{ color }}>
            {data.health_score}
            <small>/100</small>
          </div>
          <div className="score-meta">
            <span className={`pill ${data.status}`}>{STATUS_LABEL[data.status]}</span>
            <span className="delta">{data.signals.length ? plural(data.signals.length, 'warning sign') : 'No warning signs'}</span>
          </div>
        </div>
      </section>

      <Pulse score={data.health_score} status={data.status} />

      {m.quiet && (
        <p className="notice">
          Only {plural(m.prs.merged, 'merged PR')} and {plural(m.commits.total, 'commit')} in six weeks. That's too little to say much
          about how the team is doing, so treat the score lightly.
        </p>
      )}
      {!m.uses_prs && (
        <p className="notice">
          This project doesn't use GitHub pull requests (they're switched off), so it's judged on commits only. Many large projects,
          like the Linux kernel, review code by email instead.
        </p>
      )}

      <section className="vitals" aria-label="Vital signs">
        <div className="vital">
          <div className="vital-label">Time to merge, six-week median</div>
          <div className="vital-value">
            {m.prs.median_merge_hours === null ? 'None' : wait(m.prs.median_merge_hours).value}
            {m.prs.median_merge_hours !== null && <span>{wait(m.prs.median_merge_hours).unit}</span>}
          </div>
          <div className="vital-foot">
            <span className={mergeChange && mergeChange > 0 ? 'up-bad' : 'flat'}>
              {mergeChange === null
                ? 'six-week median'
                : `${mergeChange > 0 ? '+' : '-'}${wait(Math.abs(mergeChange)).value}${wait(Math.abs(mergeChange)).unit} in ${weekly.length} wks`}
            </span>
            {/* Colored by the latest week, so a worsening trend never shows green. */}
            <Sparkline values={weekly} color={(weekly[weekly.length - 1] ?? 0) > MERGE_TARGET ? COLORS.bad : COLORS.good} />
          </div>
        </div>
        <div className="vital">
          <div className="vital-label">Reviews by one person</div>
          <div className="vital-value">
            {m.reviews.total ? m.reviews.top_share : 'None'}
            {m.reviews.total > 0 && <span>%</span>}
          </div>
          <div className="vital-foot">
            <span className={reviewShareBad ? 'up-bad' : 'flat'}>
              {m.solo ? 'solo project' : m.reviews.total ? `${m.reviews.top_reviewer}, limit is ${REVIEW_LIMIT}%` : 'no reviews on merged PRs'}
            </span>
          </div>
        </div>
        <div className="vital">
          <div className="vital-label">Open PRs</div>
          <div className="vital-value">{m.prs.open}</div>
          <div className="vital-foot">
            <span className={m.prs.stale_open >= 2 ? 'up-bad' : 'flat'}>{m.prs.stale_open} open over 3 days</span>
          </div>
        </div>
        <div className="vital">
          <div className="vital-label">Commits by top author</div>
          <div className="vital-value">
            {m.commits.total ? m.commits.top_share : 'None'}
            {m.commits.total > 0 && <span>%</span>}
          </div>
          <div className="vital-foot">
            <span className="flat">{plural(m.commits.total, 'commit', m.capped?.commits)}, {m.people === 1 ? '1 person' : `${m.people} people`}</span>
          </div>
        </div>
      </section>

      {data.signals.length > 0 && (
        <section className="signals" aria-label="What lowered the score">
          <h3>What lowered the score</h3>
          <ul>{data.signals.map((s) => <li key={s}>{s}</li>)}</ul>
        </section>
      )}

      <h2 className="section-title">The evidence</h2>
      <p className="section-sub">
        From {plural(m.prs.total, 'pull request', m.capped?.prs)} and {plural(m.commits.total, 'commit', m.capped?.commits)} in the last {m.window.days / 7} weeks.
        {(m.capped?.prs || m.capped?.commits) && ' This is a very busy project, so only the most recent 300 of each were read.'}
      </p>
      {m.uses_prs && <div className="evidence">
        <div className="panel chart">
          <h3>How long PRs waited to be merged, by week</h3>
          <p className="hint">
            Each bar holds the PRs merged that week. Its height is how long they had waited since being opened (the typical, or median, wait),
            not how many there were. A PR opened in an earlier week still counts in the week it was merged. Red means over the {MERGE_TARGET}-hour target.
            Dates are in your time zone ({m.window.timezone}), so they match what GitHub shows you.
          </p>
          <MergeChart weeks={m.prs.weekly} target={MERGE_TARGET} />
        </div>
        <div className="panel">
          <h3>{m.reviews.total ? `Who did the ${plural(m.reviews.total, 'review')}` : 'Who reviews the code'}</h3>
          <p className="hint">Share of reviews on {plural(m.reviews.reviewed_prs, 'merged PR')}</p>
          {m.reviews.total ? (
            <>
              <LoadBars counts={m.reviews.per_reviewer} limit={REVIEW_LIMIT} />
              <div className="legend"><span><i />{REVIEW_LIMIT}% limit for any one reviewer</span></div>
            </>
          ) : (
            <p className="empty">
              {m.solo
                ? 'This looks like a solo project, so there is no review load to balance.'
                : 'None of the merged PRs had a GitHub review. Changes are going in without a second pair of eyes.'}
            </p>
          )}
        </div>
      </div>}

      <h2 className="section-title">This week's report</h2>
      <p className="section-sub">Written by AI from the numbers above and past incidents. Each claim links to its source.</p>
      <div className="report">
        <div className="findings">
          {report.findings.map((f, i) => (
            <article className={`finding ${f.kind}`} key={i}>
              <div className="stripe" />
              <div className="finding-body">
                <p className="finding-kind">{KIND_LABEL[f.kind]}</p>
                <h4>{f.title}</h4>
                <p>
                  {f.detail}
                  {f.sources.map((s) => <Cite key={s} n={citeNum(s)} href={`#src${citeNum(s)}`} />)}
                </p>
              </div>
            </article>
          ))}
        </div>

        <aside className="sources" aria-label="Sources">
          <h3>Sources</h3>
          {sources.map((s) => (
            <div className="source" id={`src${s.id}`} key={s.id}>
              <Cite n={s.id} />
              <div>
                <b>{s.title}</b>
                <span className="match">{s.match}% match</span>
              </div>
            </div>
          ))}
          <div className="source" id={`src${githubNum}`}>
            <Cite n={githubNum} />
            <div>
              <b>GitHub activity</b>
              <span>{plural(m.prs.total, 'PR', m.capped?.prs)}, {plural(m.commits.total, 'commit', m.capped?.commits)}, {plural(m.reviews.total, 'review')}</span>
            </div>
          </div>
          <p className="sources-note">
            The incident report and retro are sample documents for now. Soon you'll be able to add your team's own, so reports cite your real history.
          </p>
        </aside>
      </div>

      <div className="footnote">
        <span>Generated in {data.generated_seconds}s{data.cached ? ', from a report made in the last hour' : ''}.</span>
        <span>
          {data.checks?.numbers_grounded
            ? 'Every number in this report was checked against the GitHub data and sources.'
            : data.checks
              ? `${data.checks.unsupported_numbers.length} number(s) in this report couldn't be traced to the data: ${data.checks.unsupported_numbers.join(', ')}.`
              : 'Score: start at 100, lose points for each warning sign.'}
        </span>
      </div>
    </>
  );
}
