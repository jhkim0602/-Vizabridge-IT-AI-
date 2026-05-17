# Vizabridge Intern Interview

A small Next.js app for interviewing the three French interns building the
Vizabridge AI chatbot. Used to:

1. **Understand** how the chatbot is being built (architecture, data sources,
   blockers).
2. **Share** the structured CSVs our preprocessing pipeline produced and how
   to plug them in.

Lives as `interview/` inside the larger Vizabridge data-pipeline monorepo.
The questionnaire is public — interns fill it without logging in. Submissions
are written to Vercel KV. The team reviews them at `/admin` with a hardcoded
password (`1234` / `1234`).

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS
- Vercel KV (Upstash Redis) for submissions

## Local dev

```bash
cd interview
npm install
npm run dev
# http://localhost:3000
```

Without `KV_REST_API_URL` / `KV_REST_API_TOKEN` set locally, submissions
silently fall back to download-only and `/admin` shows "storage not
configured". To exercise the full flow locally, pull the env vars from your
Vercel project with `vercel env pull` and put them in `.env.local`.

## Build / typecheck

```bash
npm run build
npm run typecheck
```

## Deploy to Vercel

1. Import the repo on Vercel. Set **Root Directory** to `interview/`.
2. Framework preset: Next.js (auto-detected).
3. In the project's **Storage** tab, create a KV store and click "Connect".
   Vercel injects `KV_REST_API_URL` and `KV_REST_API_TOKEN` automatically.
4. Redeploy.

## Viewing submissions

- Go to `/admin`, sign in with `1234` / `1234`.
- Expand any row to see the section-by-section answers and the raw JSON.
- Submissions are stored in the Redis list `vizabridge:submissions`.

## Editing the interview

- Questions live in [`lib/questions.ts`](./lib/questions.ts) — add, reorder,
  or change types (`short` / `long` / `single` / `multi`). Conditional
  questions use `dependsOn`.
- The data briefing shown mid-interview is in
  [`components/DataBriefing.tsx`](./components/DataBriefing.tsx).
- The admin password (currently `1234` / `1234`) is set in
  [`components/AdminPanel.tsx`](./components/AdminPanel.tsx) and
  [`app/api/submissions/route.ts`](./app/api/submissions/route.ts).
