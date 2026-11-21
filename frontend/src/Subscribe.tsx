import { FormEvent, useState } from 'react';
import { subscribeWeekly } from './api';

// Shown only on a team link: weekly reports are for a team's own project.
export default function Subscribe({ owner, repo, team }: { owner: string; repo: string; team: string }) {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'done' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setState('sending');
    const res = await subscribeWeekly({ email, owner, repo, team });
    setState(res.success ? 'done' : 'error');
    setMessage(res.success ? res.message : res.error);
  };

  return (
    <section className="panel subscribe" aria-label="Weekly email">
      <div>
        <h3>Get this report every Monday</h3>
        <p className="hint">
          For your team's own project: a fresh report on {owner}/{repo}, grounded in your team's documents, in your inbox each week.
          Your email is only used for this report and deleted when you unsubscribe.
        </p>
      </div>
      {state === 'done' ? (
        <p className="subscribe-done" role="status">{message}</p>
      ) : (
        <form onSubmit={submit} className="subscribe-form">
          <label htmlFor="sub-email" className="visually-hidden">Email address</label>
          <input id="sub-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" maxLength={254} />
          <button className="btn" type="submit" disabled={state === 'sending'}>{state === 'sending' ? 'Sending...' : 'Send me a confirmation'}</button>
        </form>
      )}
      {state === 'error' && <p className="error">{message}</p>}
    </section>
  );
}
