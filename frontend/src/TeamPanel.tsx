import { FormEvent, useCallback, useEffect, useState } from 'react';
import { addTeamDoc, createTeam, listTeamDocs, removeTeamDoc, TeamDoc } from './api';

export function teamLink(team: string) {
  return `${window.location.origin}${window.location.pathname}?team=${team}`;
}

function DocIcon() {
  return (
    <svg width="18" height="22" viewBox="0 0 18 22" aria-hidden="true">
      <path d="M2 1h9l5 5v14a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1z" fill="#FFFFFF" stroke="#7F8D87" strokeWidth="1.4" />
      <path d="M11 1v5h5" fill="none" stroke="#7F8D87" strokeWidth="1.4" />
      <path d="M4.5 10h8M4.5 13h8M4.5 16h5" stroke="#0E6B57" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export default function TeamPanel({
  open, onClose, team, onTeamChange, onDocsChange,
}: {
  open: boolean;
  onClose: () => void;
  team: string;
  onTeamChange: (team: string) => void;
  onDocsChange: (count: number) => void;
}) {
  const [docs, setDocs] = useState<TeamDoc[]>([]);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [fileKey, setFileKey] = useState(0);

  const refresh = useCallback(async () => {
    if (!team) return;
    const res = await listTeamDocs(team);
    if (res.success) {
      setDocs(res.documents);
      onDocsChange(res.documents.length);
    } else setError(res.error);
  }, [team, onDocsChange]);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const create = async () => {
    setBusy('Creating your team space...');
    setError('');
    const res = await createTeam();
    setBusy('');
    if (res.success) onTeamChange(res.team);
    else setError(res.error);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(teamLink(team));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Copy didn’t work here. Select the link and copy it yourself.');
    }
  };

  const add = async (e: FormEvent) => {
    e.preventDefault();
    if (!file && text.trim().length === 0) {
      setError('Paste the document text, or choose a file.');
      return;
    }
    setBusy('Reading and saving the document...');
    setError('');
    const res = await addTeamDoc(team, { title, text, file });
    setBusy('');
    if (!res.success) {
      setError(res.error);
      return;
    }
    setTitle('');
    setText('');
    setFile(null);
    setFileKey((k) => k + 1);
    // Pinecone can take a moment before a new document shows up in listings.
    setDocs((d) => [res.document, ...d]);
    onDocsChange(docs.length + 1);
    setTimeout(refresh, 3000);
  };

  const remove = async (doc: TeamDoc) => {
    setBusy(`Removing "${doc.title}"...`);
    const res = await removeTeamDoc(team, doc.id);
    setBusy('');
    if (!res.success) {
      setError(res.error);
      return;
    }
    setDocs((d) => d.filter((x) => x.id !== doc.id));
    onDocsChange(docs.length - 1);
  };

  return (
    <>
      <div className={`guide-backdrop${open ? ' open' : ''}`} onClick={onClose} aria-hidden="true" />
      <aside className={`guide${open ? ' open' : ''}`} role="dialog" aria-label="Your team's history" aria-hidden={!open}>
        <header className="guide-head">
          <div>
            <h2>Your team's history</h2>
            <p>Reports cite your own incidents and retros</p>
          </div>
          <button type="button" className="guide-close" onClick={onClose} aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></svg>
          </button>
        </header>

        <div className="guide-body">
          {!team ? (
            <section className="guide-section">
              <p>
                Out of the box, reports compare a project with two sample documents about an example team. Add your own incident reports,
                retrospectives and postmortems, and every report will be grounded in what actually happened to your team.
              </p>
              <ol>
                <li>Create a team space. You get a private link.</li>
                <li>Add documents by pasting text or uploading a .txt, .md or .pdf file.</li>
                <li>Analyze any project from your link. The report cites your documents.</li>
              </ol>
              <p className="team-warn">This is a demo, so please don't add anything confidential.</p>
              <button type="button" className="btn wide" onClick={create} disabled={!!busy}>
                {busy || 'Create a team space'}
              </button>
            </section>
          ) : (
            <>
              <section className="guide-section">
                <h3>Your private link</h3>
                <p>Anyone with this link can see and change your team's documents. Bookmark it, and share it only with your team.</p>
                <div className="team-link">
                  <input id="team-link" readOnly value={teamLink(team)} onFocus={(e) => e.target.select()} aria-label="Your team link" />
                  <button type="button" className="chip" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
                </div>
              </section>

              <section className="guide-section">
                <h3>Add a document</h3>
                <form className="team-form" onSubmit={add}>
                  <label htmlFor="doc-title">Title <span>(optional)</span></label>
                  <input id="doc-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Checkout outage, June 2025" maxLength={120} />
                  <label htmlFor="doc-text">Paste the text</label>
                  <textarea id="doc-text" value={text} onChange={(e) => setText(e.target.value)} disabled={!!file}
                    placeholder="What happened, why, and what you changed afterwards..." />
                  <label htmlFor="doc-file">Or upload a file <span>(.txt, .md or .pdf, up to 2 MB)</span></label>
                  <input key={fileKey} id="doc-file" type="file" accept=".txt,.md,.markdown,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
                  <p className="team-warn">This is a demo, so please don't add anything confidential.</p>
                  <button type="submit" className="btn wide" disabled={!!busy}>{busy || 'Add document'}</button>
                </form>
              </section>

              <section className="guide-section">
                <h3>{docs.length ? `${docs.length} document${docs.length === 1 ? '' : 's'}` : 'No documents yet'}</h3>
                {docs.length === 0 && <p>Until you add one, reports use the sample documents.</p>}
                <ul className="team-docs">
                  {docs.map((d) => (
                    <li key={d.id}>
                      <DocIcon />
                      <div>
                        <b>{d.title}</b>
                        <span>{d.added ? `Added ${new Date(d.added).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}` : 'Just added'}</span>
                      </div>
                      <button type="button" className="team-remove" onClick={() => remove(d)} disabled={!!busy} aria-label={`Remove ${d.title}`}>Remove</button>
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}
          {error && <p className="error banner" role="alert">{error}</p>}
        </div>

        <footer className="guide-foot">
          <button type="button" className="btn" onClick={onClose}>Done</button>
        </footer>
      </aside>
    </>
  );
}
