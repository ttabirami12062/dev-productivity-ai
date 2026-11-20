import { ReactNode, useEffect } from 'react';

// Numbers here must match src/metrics.py (24h target, 50% review limit, 3-day stale,
// point deductions) and the six-week window in src/github_client.py.

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="guide-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function Term({ word, children }: { word: string; children: ReactNode }) {
  return (
    <div className="term">
      <dt>{word}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export default function Guide({ open, onClose, timeZone }: { open: boolean; onClose: () => void; timeZone: string }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  return (
    <>
      <div className={`guide-backdrop${open ? ' open' : ''}`} onClick={onClose} aria-hidden="true" />
      <aside className={`guide${open ? ' open' : ''}`} role="dialog" aria-label="How to read this dashboard" aria-hidden={!open}>
        <header className="guide-head">
          <div>
            <h2>How to read this</h2>
            <p>Everything on the page, in plain words</p>
          </div>
          <button type="button" className="guide-close" onClick={onClose} aria-label="Close">
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></svg>
          </button>
        </header>

        <div className="guide-body">
          <Section title="What this is">
            <p>
              Software teams slow down quietly: code waits days to be checked, or one person ends up checking everything and burns out.
              This tool reads a GitHub project's last six weeks of activity, spots those warning signs, and writes a short report on what to do
              about them this week.
            </p>
          </Section>

          <Section title="How to use it">
            <ol>
              <li>Type a public GitHub project as <code>owner/name</code> (for example <code>vercel/swr</code>), or paste its GitHub link.</li>
              <li>Press Analyze. The first report of the day can take up to a minute while the server wakes up. After that it takes a few seconds.</li>
              <li>Read from top to bottom: the headline, the score, the four numbers, the reasons, the charts, then the report.</li>
              <li>The same project is remembered for an hour, so asking again is instant.</li>
            </ol>
          </Section>

          <Section title="Five words you'll see">
            <dl>
              <Term word="Repository">One project's code on GitHub, named owner/name.</Term>
              <Term word="Commit">One saved change to the code.</Term>
              <Term word="Pull request (PR)">"Here's my change, please check it before it goes in."</Term>
              <Term word="Review">A teammate checking a PR, then approving it or asking for changes.</Term>
              <Term word="Merge">The PR is accepted and becomes part of the project.</Term>
            </dl>
          </Section>

          <Section title="The health score">
            <p>It starts at 100 and loses points for each warning sign. The reasons are listed under "What lowered the score".</p>
            <table className="guide-table">
              <tbody>
                <tr><td>PRs wait over 24 hours to merge</td><td>-12</td></tr>
                <tr><td>Over 2 days</td><td>-25</td></tr>
                <tr><td>Over a week</td><td>-35</td></tr>
                <tr><td>Waits have doubled in recent weeks</td><td>-10</td></tr>
                <tr><td>2 to 4 PRs open for over 3 days</td><td>-8</td></tr>
                <tr><td>5 or more PRs open for over 3 days</td><td>-15</td></tr>
                <tr><td>One person does over half the reviews</td><td>-12</td></tr>
                <tr><td>One person does over 70% of the reviews</td><td>-25</td></tr>
                <tr><td>One person makes over 80% of the commits</td><td>-10</td></tr>
              </tbody>
            </table>
            <p>
              <b>Healthy</b> is 80 or more, <b>worth watching</b> is 60 to 79, <b>at risk</b> is under 60. A project with almost no activity shows
              <b> too little activity</b> instead, because a score from a handful of changes means very little. Solo projects are never marked down for
              having one person do everything.
            </p>
          </Section>

          <Section title="The four numbers">
            <dl>
              <Term word="Time to merge">
                The typical wait from opening a PR to merging it (the median, so one very slow PR can't skew it). Under 24 hours is good. The small line
                shows how it changed over the six weeks.
              </Term>
              <Term word="Reviews by one person">
                The busiest reviewer's share of all reviews on recently merged PRs. Over 50% means one person is becoming a bottleneck, and a
                burnout risk if they're overloaded.
              </Term>
              <Term word="Open PRs">
                Changes still waiting, and how many have waited more than 3 days. A growing pile of old PRs means work is stuck.
              </Term>
              <Term word="Commits by top author">
                How much of the code one person writes. High is normal for small projects, but in a team it means knowledge sits with one person.
              </Term>
            </dl>
          </Section>

          <Section title="The two charts">
            <p>
              <b>How long PRs waited, by week.</b> Each bar is one week and holds the PRs <i>merged</i> that week. Its height is how long they had
              waited since being opened, not how many there were; the count is written under the bar. A PR opened in an earlier week still counts in the
              week it was merged, with its whole wait. Red bars are over the 24-hour target, shown as the dashed line.
            </p>
            <p>
              <b>Who did the reviews.</b> One bar per person, showing their share of reviews. The dashed line is the 50% limit, and anyone past it turns
              red.
            </p>
          </Section>

          <Section title="The report">
            <p>An AI writes it from the numbers on this page and from past incident reports, following strict rules: only use these numbers, invent nothing.</p>
            <ul className="kinds">
              <li><span className="k risk" />Risk: something likely to cause trouble soon.</li>
              <li><span className="k action" />Do this week: a concrete step to take.</li>
              <li><span className="k positive" />Going well: something worth keeping.</li>
            </ul>
            <p>
              The small numbered tags show where each claim came from. Tap one to jump to it in Sources. The last source is always the GitHub activity
              itself.
            </p>
            <p>
              Every number the AI writes is checked against the data it was given, and the note at the bottom of the report says whether they all
              matched. Separately, the project's automated tests use a second AI to confirm each cited source really supports its claim.
            </p>
          </Section>

          <Section title="Sources and match %">
            <p>
              Before writing, the tool searches a library of past incident reports and team retrospectives for the ones most like this week's warning signs.
              The match % is how similar each one is. This is called retrieval: look things up first, then write, so advice comes from real lessons rather
              than generic tips.
            </p>
            <p>
              For now the library holds two sample documents about an example team, so every project is compared with the same examples. Soon teams will be
              able to add their own.
            </p>
          </Section>

          <Section title="Dates and times">
            <p>
              Everything uses your time zone, <b>{timeZone}</b>, so dates match what GitHub shows you. This matters: a PR merged at 7:30pm on October 11 in
              Oklahoma is already October 12 in London, and could land in a different week's bar if the two clocks were mixed up.
            </p>
            <p>The six weeks end at midnight tonight, your time, and each week runs from midnight to midnight.</p>
          </Section>

          <Section title="What it can't see">
            <ul>
              <li>Only public projects, and only the last six weeks.</li>
              <li>Very busy projects: up to 300 PRs and 300 commits. Reviews are counted on every PR merged in the six weeks.</li>
              <li>Bots, the automatic accounts that update things, are left out.</li>
              <li>Some projects, like the Linux kernel, turn pull requests off and review by email. They're judged on commits only.</li>
            </ul>
          </Section>

          <Section title="Privacy">
            <p>
              The tool only reads public activity: who opened, reviewed and merged what, and when. It never reads the code itself, and it doesn't keep any
              results after an hour. Feedback you send goes only to the developer by email and is never shown on the site.
            </p>
          </Section>
        </div>

        <footer className="guide-foot">
          <button type="button" className="btn" onClick={onClose}>Got it</button>
        </footer>
      </aside>
    </>
  );
}
