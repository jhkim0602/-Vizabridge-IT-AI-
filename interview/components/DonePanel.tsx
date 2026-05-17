"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ALL_QUESTIONS, SECTIONS } from "@/lib/questions";
import type { Answers, Question } from "@/lib/types";

interface Submission {
  intervieweeName: string;
  intervieweeEmail: string;
  intervieweeRole: string;
  submittedAt: string;
  startedAt: string;
  durationSeconds: number;
  answers: Answers;
}

const SUBMISSION_KEY = "vizabridge-interview-submission-v1";
const RECIPIENT_EMAIL = "data-team@vizabridge.example";

function formatValue(q: Question, value: string | string[] | undefined): string {
  if (value === undefined) return "(no answer)";
  if (Array.isArray(value)) {
    if (value.length === 0) return "(no answer)";
    return value
      .map((v) => q.options?.find((o) => o.value === v)?.label ?? v)
      .join(", ");
  }
  if (q.options) {
    return q.options.find((o) => o.value === value)?.label ?? value;
  }
  return value.trim() || "(no answer)";
}

function buildMarkdown(sub: Submission): string {
  const lines: string[] = [];
  lines.push("# Vizabridge Intern Interview Response");
  lines.push("");
  lines.push(`- **Name:** ${sub.intervieweeName || "(blank)"}`);
  lines.push(`- **Email:** ${sub.intervieweeEmail || "(blank)"}`);
  if (sub.intervieweeRole) lines.push(`- **Role:** ${sub.intervieweeRole}`);
  lines.push(`- **Submitted:** ${sub.submittedAt}`);
  lines.push(
    `- **Duration:** ${Math.round(sub.durationSeconds / 60)} minutes`,
  );
  lines.push("");

  for (const section of SECTIONS) {
    lines.push(`## ${section.title} (${section.titleKo})`);
    lines.push("");
    for (const q of section.questions) {
      const val = sub.answers[q.id];
      lines.push(`### ${q.number} — ${q.prompt}`);
      if (q.promptKo) lines.push(`_${q.promptKo}_`);
      lines.push("");
      lines.push(formatValue(q, val));
      lines.push("");
    }
  }
  return lines.join("\n");
}

export function DonePanel() {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(SUBMISSION_KEY);
      if (raw) setSubmission(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  if (!submission) {
    return (
      <div className="card">
        <h1 className="text-xl font-semibold text-ink-900">
          No submission found
        </h1>
        <p className="mt-2 text-sm text-ink-600">
          We couldn't find a finished interview in this browser. If you
          haven't started yet, head to the interview.
        </p>
        <div className="mt-4">
          <Link href="/interview" className="btn-primary">
            Go to the interview
          </Link>
        </div>
      </div>
    );
  }

  const markdown = buildMarkdown(submission);
  const json = JSON.stringify(submission, null, 2);
  const slugName = submission.intervieweeName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
  const filenameBase = `vizabridge-interview-${slugName || "response"}-${submission.submittedAt.slice(0, 10)}`;

  function download(content: string, ext: string, mime: string) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filenameBase}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function copyMarkdown() {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  const mailtoBody = encodeURIComponent(
    `Hi Vizabridge data team,\n\nMy interview response is below.\n\n${markdown}`,
  );
  const mailtoSubject = encodeURIComponent(
    `Vizabridge interview response — ${submission.intervieweeName || "intern"}`,
  );
  const mailtoHref = `mailto:${RECIPIENT_EMAIL}?subject=${mailtoSubject}&body=${mailtoBody}`;

  return (
    <div className="space-y-6">
      <section className="card">
        <span className="chip">Done · merci!</span>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink-900">
          Thanks, {submission.intervieweeName || "there"}.
        </h1>
        <p className="mt-2 text-sm text-ink-600">
          Your answers are saved in this browser tab. To get them to the data
          team, pick one of the options below — nothing is uploaded
          automatically.
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="btn-primary"
            onClick={() => download(json, "json", "application/json")}
          >
            Download JSON
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              download(markdown, "md", "text/markdown;charset=utf-8")
            }
          >
            Download Markdown
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={copyMarkdown}
          >
            {copied ? "Copied!" : "Copy Markdown"}
          </button>
          <a className="btn-ghost" href={mailtoHref}>
            Email to the data team
          </a>
        </div>
        <p className="mt-2 text-xs text-ink-500">
          Default recipient is{" "}
          <span className="font-mono">{RECIPIENT_EMAIL}</span> — change it in
          your mail client if needed.
        </p>
      </section>

      <section className="card">
        <h2 className="text-lg font-semibold text-ink-900">Your answers</h2>
        <p className="mt-1 text-xs text-ink-500">
          {ALL_QUESTIONS.length} questions · submitted at{" "}
          {submission.submittedAt}
        </p>
        <div className="mt-6 space-y-8">
          {SECTIONS.map((section) => (
            <div key={section.id}>
              <h3 className="text-sm font-semibold text-ink-900">
                {section.title}{" "}
                <span className="text-xs font-normal text-ink-500">
                  ({section.titleKo})
                </span>
              </h3>
              <dl className="mt-3 space-y-4">
                {section.questions.map((q) => (
                  <div
                    key={q.id}
                    className="rounded-md border border-ink-200 bg-ink-50/40 p-3"
                  >
                    <dt className="text-xs font-semibold text-ink-700">
                      {q.number} · {q.prompt}
                    </dt>
                    <dd className="mt-1 whitespace-pre-wrap text-sm text-ink-900">
                      {formatValue(q, submission.answers[q.id])}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
