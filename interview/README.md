# Vizabridge Intern Interview

A small Next.js app for interviewing the three French interns building the
Vizabridge AI chatbot. Used to:

1. **Understand** how the chatbot is being built (architecture, data sources,
   blockers).
2. **Share** the structured CSVs our preprocessing pipeline produced and how
   to plug them in.

Lives as `interview/` inside the larger Vizabridge data-pipeline monorepo. No
backend — answers stay in the browser; the interviewee downloads or emails
their response at the end.

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS
- No database, no auth, no analytics

## Local dev

```bash
cd interview
npm install
npm run dev
# http://localhost:3000
```

## Build / typecheck

```bash
npm run build
npm run typecheck
```

## Deploy to Vercel

1. Import the repo on Vercel.
2. Set **Root Directory** to `interview/`.
3. Framework preset: Next.js (auto-detected).
4. No environment variables required.

## Editing the interview

- Questions live in [`lib/questions.ts`](./lib/questions.ts) — add, reorder,
  or change types (`short` / `long` / `single` / `multi`). Conditional
  questions use `dependsOn`.
- The data briefing shown mid-interview is in
  [`components/DataBriefing.tsx`](./components/DataBriefing.tsx).
- The recipient email on the done page is the `RECIPIENT_EMAIL` constant in
  [`components/DonePanel.tsx`](./components/DonePanel.tsx) — change it before
  sharing the link with the interns.
