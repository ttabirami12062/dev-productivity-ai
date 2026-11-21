# Changelog

What changed in Dev Productivity AI, newest first, in plain language. The commit history has the full details of each change.

## November 2026: rebuilt from a demo into a working product

In November the live site had stopped working, and a full review of the code found the causes. This section is the rebuild, grouped by theme.

### Fixed what was broken
- **The AI model had been retired.** `gpt-3.5-turbo` no longer existed, so every report failed. Reports now use `gpt-5.4-mini`, chosen after a side-by-side test against two other models (it was fastest at 2.2s, against 5.8s for `gpt-4o-mini`, and wrote the most specific headlines). The model can be changed with a setting, without touching code.
- **The GitHub token had expired**, and the old code quietly turned the rejection into a perfect 100/100 score. Errors are now caught and explained.
- **Library versions weren't pinned**, so any new release could break the site on its next deploy. Every library is now locked to a tested version.

### Privacy and security
- **Feedback emails were public.** Anyone could read every visitor's name and email at `/reviews`, and the file was committed to GitHub. The page was removed and the file erased from the whole Git history.
- The AI report is no longer inserted into the page as raw HTML, which could have run code from a malicious repository.
- Weekly emails can only be set up from a team space, and every address must be confirmed first, so nobody can be signed up by someone else or follow a stranger's team.
- Uploaded team documents are treated as reference only. A document saying "ignore your rules" was tested and ignored.

### Real signals instead of three rules
- Six weeks of pull requests, reviews and commits, fetched with GitHub GraphQL in 1 to 3 requests instead of up to 45 (a busy repo went from 9.3s to 4.4s with identical results).
- Eleven signals: time to merge, time to first review, cycle time, review load, unreviewed merges, PRs waiting for a first look, stuck PRs, PR size, files that keep needing fixes, commit concentration and after-hours work on each author's own clock.
- A score that explains itself: every point lost comes with a sentence saying why. Solo projects aren't penalized for being solo, nearly empty projects say "too little activity", and projects without pull requests, like the Linux kernel, are judged on commits.
- Weeks and dates follow the visitor's own time zone, after testing showed a PR merged on a US evening landing in the wrong week in UTC.

### Reports you can trust
- Reports are structured findings (risks, actions, what's going well), each citing numbered sources with a match score.
- Every number in a live report is checked against the data it came from, and visitors are told when everything matched.
- A second AI judges, on every push, whether each cited source really supports its claim. It caught real overstatements, which were fixed in the instructions rather than by lowering the bar: risks raised for a healthy team, an old incident cited for today's numbers, and a forced "going well" note claiming PRs were on track while three were stuck.
- Langfuse records every report's steps, time, tokens and cost (about $0.0025 a report). Visitor ratings are stored on the report they're about.

### Your team's own history
- Team spaces: a private link where a team adds its incident reports and retros (pasted, .txt, .md or .pdf). Reports from that link cite the team's documents, labelled "Your team's document". Each team's documents live in their own Pinecone namespace.

### Trends and weekly emails
- Track a project and its numbers are saved every night in Supabase, by a free scheduled job that uses no AI. The dashboard shows the score day by day and how it compares with a month earlier.
- From a team space, subscribe to a Monday email with the project's report. One click unsubscribes and deletes the address, either from the email or with Gmail's own Unsubscribe button.

### Design and ease of use
- A new light design, the "team vitals chart": a plain-language headline, the score, a heartbeat line, vital signs with trend lines, charts that can't be misread, and the cited report.
- A "How to read this" panel that explains every number, chart, rule and limit in plain words.
- Clear messages instead of raw errors, a "waking up the server" note, and a layout that works on phones.
- The frontend moved from Create React App, which is no longer maintained, to Vite. Builds take about 2 seconds.

### Running it reliably and cheaply
- A one-hour cache, a per-visitor hourly limit and a daily cap of new reports keep AI costs predictable, on top of prepaid credits.
- A health check every 10 minutes keeps the free server awake, and the nightly job keeps the free database from pausing.
- Tests on every push: scoring math, the number checker, uploads, history, emails, the frontend, and an AI-judged evaluation of six team scenarios.
- Tested against twelve real projects before going live, which found and fixed two bugs.

## March 2026: first version

- Phase 1: GitHub data, three health score rules, and a report from `gpt-3.5-turbo`.
- Phase 2: RAG over two sample documents in Pinecone.
- Phase 3: Langfuse setup and a CI evaluation that checked reports for keywords.
- A dark-themed React dashboard with a feedback form, deployed on Vercel and Render.
