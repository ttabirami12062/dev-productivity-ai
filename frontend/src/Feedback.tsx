import { FormEvent, useState } from 'react';
import { sendFeedback } from './api';

function Star({ filled }: { filled: boolean }) {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.3L12 17.1l-5.7 3.1 1.2-6.3L2.8 9.5l6.4-.8z"
        fill={filled ? '#F2B705' : 'none'} stroke={filled ? '#C99700' : '#B8C2BD'} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

export default function Feedback({ owner, repo, traceId }: { owner: string; repo: string; traceId?: string | null }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'failed'>('idle');

  if (state === 'sent') {
    return (
      <section className="feedback done">
        <h3>Thanks for the feedback</h3>
        <p>If you left your email, I'll reply personally. I'd love to hear how this could help your team.</p>
      </section>
    );
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!rating) return;
    setState('sending');
    const ok = await sendFeedback({ owner, repo, rating, comment, name, user_email: email, role, trace_id: traceId });
    setState(ok ? 'sent' : 'failed');
  };

  return (
    <form className="feedback" onSubmit={submit}>
      <h3>Was this report useful?</h3>
      <p>If you lead an engineering team, I'd love to hear what you think.</p>
      <div className="stars" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} star${n > 1 ? 's' : ''}`} onClick={() => setRating(n)}>
            <Star filled={rating >= n} />
          </button>
        ))}
      </div>
      <div className="form-grid">
        <label>Name<input id="fb-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Optional" maxLength={100} /></label>
        <label>Email<input id="fb-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Optional" maxLength={200} /></label>
        <label className="wide">Role<input id="fb-role" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Engineering manager, tech lead..." maxLength={100} /></label>
        <label className="wide">Comments<textarea id="fb-comment" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="What would make this useful for your team?" maxLength={2000} /></label>
      </div>
      {state === 'failed' && <p className="error">That didn't send. Please try again in a moment.</p>}
      <button className="btn" type="submit" disabled={!rating || state === 'sending'}>
        {state === 'sending' ? 'Sending...' : rating ? 'Send feedback' : 'Pick a rating first'}
      </button>
      <p className="privacy">Your name and email are only sent to me by email. They're never shown on this site.</p>
    </form>
  );
}
