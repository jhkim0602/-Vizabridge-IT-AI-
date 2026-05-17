"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { SECTIONS } from "@/lib/questions";
import type { Answers, Question } from "@/lib/types";
import { clearDraft, loadDraft, saveDraft } from "@/lib/storage";
import { QuestionField } from "./QuestionField";
import { DataBriefing } from "./DataBriefing";

const SUBMISSION_KEY = "vizabridge-interview-submission-v1";

function isQuestionVisible(q: Question, answers: Answers): boolean {
  if (!q.dependsOn) return true;
  const dep = answers[q.dependsOn.questionId];
  if (!dep) return false;
  const depArr = Array.isArray(dep) ? dep : [dep];
  return q.dependsOn.values.some((v) => depArr.includes(v));
}

function isQuestionAnswered(
  q: Question,
  value: string | string[] | undefined,
): boolean {
  if (q.optional) return true;
  if (value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  return value.length > 0;
}

export function InterviewForm() {
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);
  const [sectionIndex, setSectionIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [intervieweeName, setName] = useState("");
  const startedAtRef = useRef<string>(new Date().toISOString());

  useEffect(() => {
    const draft = loadDraft();
    if (draft) {
      setSectionIndex(draft.sectionIndex ?? 0);
      setAnswers(draft.answers ?? {});
      setName(draft.intervieweeName ?? "");
      startedAtRef.current = draft.startedAt ?? startedAtRef.current;
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    saveDraft({
      intervieweeName,
      answers,
      startedAt: startedAtRef.current,
      sectionIndex,
    });
  }, [hydrated, intervieweeName, answers, sectionIndex]);

  const section = SECTIONS[sectionIndex];
  const isLast = sectionIndex === SECTIONS.length - 1;
  const isFirst = sectionIndex === 0;
  const isBriefing = section?.id === "data_briefing";

  const visibleQuestions = useMemo(
    () => section.questions.filter((q) => isQuestionVisible(q, answers)),
    [section, answers],
  );

  const introNeedsContact = isFirst;
  const contactValid = intervieweeName.trim().length > 0;

  const sectionComplete = useMemo(() => {
    if (introNeedsContact && !contactValid) return false;
    return visibleQuestions.every((q) =>
      isQuestionAnswered(q, answers[q.id]),
    );
  }, [
    introNeedsContact,
    contactValid,
    visibleQuestions,
    answers,
  ]);

  const totalSections = SECTIONS.length;
  const progress = Math.round(((sectionIndex + 1) / totalSections) * 100);

  function setAnswer(id: string, value: string | string[]) {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  }

  function goNext() {
    if (!sectionComplete) return;
    if (isLast) {
      finishInterview();
      return;
    }
    setSectionIndex((i) => Math.min(i + 1, SECTIONS.length - 1));
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  function goPrev() {
    setSectionIndex((i) => Math.max(0, i - 1));
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  function finishInterview() {
    const submission = {
      intervieweeName,
      submittedAt: new Date().toISOString(),
      startedAt: startedAtRef.current,
      durationSeconds: Math.round(
        (Date.now() - new Date(startedAtRef.current).getTime()) / 1000,
      ),
      answers,
    };
    try {
      window.sessionStorage.setItem(
        SUBMISSION_KEY,
        JSON.stringify(submission),
      );
    } catch {
      // ignore
    }
    fetch("/api/submissions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(submission),
      keepalive: true,
    }).catch(() => {
      // ignore — local download still works as a backup
    });
    clearDraft();
    router.push("/done");
  }

  if (!hydrated) {
    return (
      <div className="card">
        <p className="text-sm text-ink-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
            Section {sectionIndex + 1} of {totalSections} · {section.duration}
          </p>
          <p className="text-xs text-ink-500">{progress}%</p>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-ink-200">
          <div
            className="h-full bg-brand-600 transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <header className="card">
        <p className="text-xs text-ink-500">{section.titleKo}</p>
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-900 sm:text-2xl">
          {section.title}
        </h1>
        {section.intro && (
          <p className="mt-3 text-sm text-ink-600">{section.intro}</p>
        )}
        {section.introKo && (
          <p className="mt-1 text-xs text-ink-500">{section.introKo}</p>
        )}

        {introNeedsContact && (
          <div className="mt-6 border-t border-ink-200 pt-6">
            <label className="field-label" htmlFor="name">
              Your name *
            </label>
            <input
              id="name"
              type="text"
              className="input-base"
              placeholder="e.g. Jeanne Dupont"
              value={intervieweeName}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
        )}
      </header>

      {isBriefing ? (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="card">
            <DataBriefing />
          </div>
          <div className="card">
            <h3 className="text-sm font-semibold text-ink-900">
              Confirm you've read it
            </h3>
            <p className="mt-1 text-xs text-ink-500">
              브리핑을 다 읽으셨다면 아래 버튼을 눌러주세요.
            </p>
            <div className="mt-4 space-y-6">
              {visibleQuestions.map((q) => (
                <QuestionField
                  key={q.id}
                  question={q}
                  value={answers[q.id]}
                  onChange={(v) => setAnswer(q.id, v)}
                />
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="card space-y-8">
          {visibleQuestions.map((q) => (
            <QuestionField
              key={q.id}
              question={q}
              value={answers[q.id]}
              onChange={(v) => setAnswer(q.id, v)}
            />
          ))}
        </div>
      )}

      <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          className="btn-secondary"
          onClick={goPrev}
          disabled={isFirst}
        >
          ← Back
        </button>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {!sectionComplete && (
            <p className="text-right text-xs text-ink-500">
              {introNeedsContact && !contactValid
                ? "Please enter your name to begin."
                : "Answer the remaining required questions to continue."}
            </p>
          )}
          <button
            type="button"
            className="btn-primary"
            onClick={goNext}
            disabled={!sectionComplete}
          >
            {isLast ? "Finish & review →" : "Next section →"}
          </button>
        </div>
      </div>
    </div>
  );
}
