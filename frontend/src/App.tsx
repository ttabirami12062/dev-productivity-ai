import { useEffect, useState } from 'react';
import { analyzeRepo, parseRepo, timeZone } from './api';
import { BrandMark } from './charts';
import Dashboard from './Dashboard';
import Feedback from './Feedback';
import Guide from './Guide';
import { Analysis } from './types';

const EXAMPLES = ['vercel/swr', 'pallets/flask', 'fastapi/fastapi'];

function Loading({ seconds }: { seconds: number }) {
  return (
    <section className="loading" aria-live="polite">
      <div className="loading-bar"><span /></div>
      <p className="loading-title">
        {seconds < 6 ? 'Reading six weeks of pull requests, reviews and commits...' : seconds < 20 ? 'Comparing this week with past incidents and writing the report...' : 'Waking up the server...'}
      </p>
      {seconds >= 6 && (
        <p className="loading-sub">
          The server sleeps when nobody has used it for a while, so the first report of the day can take up to a minute. After that it's quick.
        </p>
      )}
    </section>
  );
}

export default function App() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Analysis | null>(null);
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    if (!loading) return;
    const started = Date.now();
    const t = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(t);
  }, [loading]);

  const run = async (value: string) => {
    const parsed = parseRepo(value);
    if (!parsed) {
      setError('Type a GitHub repository like vercel/swr, or paste its link.');
      return;
    }
    setInput(`${parsed.owner}/${parsed.repo}`);
    setError('');
    setResult(null);
    setSeconds(0);
    setLoading(true);
    const res = await analyzeRepo(parsed.owner, parsed.repo);
    setLoading(false);
    if (res.success) setResult(res);
    else setError(res.error);
  };

  return (
    <div className="page">
      <div className="wrap">
        <header className="top">
          <a className="brand" href="/" aria-label="Dev Productivity AI home">
            <BrandMark />
            Dev Productivity AI
          </a>
          <form className="repo-form" onSubmit={(e) => { e.preventDefault(); run(input); }}>
            <label htmlFor="repo">GitHub repository</label>
            <input id="repo" value={input} onChange={(e) => setInput(e.target.value)} placeholder="owner/repository" autoComplete="off" spellCheck={false} />
            <button className="btn" type="submit" disabled={loading}>{loading ? 'Analyzing...' : 'Analyze'}</button>
          </form>
          <button type="button" className="guide-open" onClick={() => setGuideOpen(true)}>
            <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true">
              <circle cx="10" cy="10" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
              <path d="M7.6 7.6a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              <circle cx="10" cy="14.6" r="1" fill="currentColor" />
            </svg>
            How to read this
          </button>
        </header>

        {error && <p className="error banner" role="alert">{error}</p>}

        {!result && !loading && (
          <section className="intro">
            <p className="eyebrow">Team health for engineering managers</p>
            <h1>See burnout and bottlenecks <mark>weeks before a deadline slips.</mark></h1>
            <p className="summary">
              Enter any public GitHub repository. You'll get a health score, the signals behind it, and a short weekly report
              that links every recommendation to past incidents.
            </p>
            <div className="examples">
              <span>Try one:</span>
              {EXAMPLES.map((ex) => (
                <button key={ex} type="button" className="chip" onClick={() => run(ex)}>{ex}</button>
              ))}
            </div>
            <ul className="how">
              <li><b>Time to merge</b><span>How long PRs wait, week by week, against a 24-hour target.</span></li>
              <li><b>Review load</b><span>Whether one person is quietly reviewing everything.</span></li>
              <li><b>Cited report</b><span>What to do this week, with the source behind each step.</span></li>
            </ul>
          </section>
        )}

        {loading && <Loading seconds={seconds} />}

        {result && (
          <>
            <Dashboard data={result} />
            <Feedback owner={result.owner} repo={result.repo} />
          </>
        )}

        <Guide open={guideOpen} onClose={() => setGuideOpen(false)} timeZone={timeZone} />

        <footer className="foot">
          <span>Built by Abirami Thiyagarajan</span>
          <a href="https://github.com/ttabirami12062/dev-productivity-ai">Source on GitHub</a>
        </footer>
      </div>
    </div>
  );
}
