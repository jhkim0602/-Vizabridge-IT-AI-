"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ALL_QUESTIONS, SECTIONS } from "@/lib/questions";
import type { Answers, Question } from "@/lib/types";

interface Submission {
  intervieweeName: string;
  submittedAt: string;
  startedAt: string;
  durationSeconds: number;
  answers: Answers;
}

const SUBMISSION_KEY = "vizabridge-interview-submission-v1";

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

export function DonePanel() {
  const [submission, setSubmission] = useState<Submission | null>(null);

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

  return (
    <div className="space-y-6">
      <section className="card">
        <span className="chip">Done · merci!</span>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink-900">
          Thank you so much, {submission.intervieweeName || "there"}.
        </h1>
        <p className="mt-3 text-sm leading-6 text-ink-600">
          We truly appreciate you taking the time to share your work and
          thoughts with us. Your responses have been received — we will read
          every answer carefully and follow up if anything needs
          clarification. Wishing you the best with the rest of the build.
        </p>
        <p className="mt-3 text-xs text-ink-500">
          소중한 시간 내어 답변해 주셔서 진심으로 감사드립니다. 응답은 모두
          잘 도착했고, 한 분 한 분의 내용을 꼼꼼히 읽어보겠습니다. 앞으로의
          작업에도 좋은 결과 있으시길 바랍니다.
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
