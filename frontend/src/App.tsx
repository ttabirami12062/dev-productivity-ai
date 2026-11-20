import { useEffect, useState } from 'react';
import { analyzeRepo, parseRepo } from './api';
import { BrandMark } from './charts';
import Dashboard from './Dashboard';
import Feedback from './Feedback';
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

        <footer className="foot">
          <span>Built by Abirami Thiyagarajan</span>
          <a href="https://github.com/ttabirami12062/dev-productivity-ai">Source on GitHub</a>
        </footer>
      </div>
    </div>
  );
}
