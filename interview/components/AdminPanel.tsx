"use client";

import { useEffect, useState } from "react";
import { ALL_QUESTIONS, SECTIONS } from "@/lib/questions";
import type { Answers, Question } from "@/lib/types";

interface StoredSubmission {
  receivedAt?: string;
  intervieweeName: string;
  submittedAt: string;
  startedAt: string;
  durationSeconds: number;
  answers: Answers;
}

const SESSION_KEY = "vizabridge-admin-token-v1";
const ADMIN_ID = "1234";
const ADMIN_PW = "1234";

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

export function AdminPanel() {
  const [token, setToken] = useState<string | null>(null);
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<StoredSubmission[] | null>(null);
  const [openIdx, setOpenIdx] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const t = sessionStorage.getItem(SESSION_KEY);
    if (t) setToken(t);
  }, []);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetch(`/api/submissions?token=${encodeURIComponent(token)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(String(r.status));
        const j = await r.json();
        setItems(j.items ?? []);
      })
      .catch(() => {
        setError("Failed to load submissions.");
        sessionStorage.removeItem(SESSION_KEY);
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  function login(e: React.FormEvent) {
    e.preventDefault();
    if (id === ADMIN_ID && pw === ADMIN_PW) {
      sessionStorage.setItem(SESSION_KEY, ADMIN_PW);
      setToken(ADMIN_PW);
      setError(null);
    } else {
      setError("Invalid credentials.");
    }
  }

  function logout() {
    sessionStorage.removeItem(SESSION_KEY);
    setToken(null);
    setItems(null);
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-sm">
        <form onSubmit={login} className="card space-y-4">
          <h1 className="text-lg font-semibold text-ink-900">Admin login</h1>
          <div>
            <label className="field-label" htmlFor="aid">
              ID
            </label>
            <input
              id="aid"
              className="input-base"
              value={id}
              onChange={(e) => setId(e.target.value)}
              autoComplete="off"
            />
          </div>
          <div>
            <label className="field-label" htmlFor="apw">
              Password
            </label>
            <input
              id="apw"
              type="password"
              className="input-base"
              value={pw}
              onChange={(e) => setPw(e.target.value)}
              autoComplete="off"
            />
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button type="submit" className="btn-primary w-full">
            Sign in
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">
            Submissions{" "}
            <span className="ml-2 text-sm font-normal text-ink-500">
              {items ? `${items.length} total` : ""}
            </span>
          </h1>
          <p className="mt-1 text-xs text-ink-500">
            Stored on the server at <span className="font-mono">data/submissions.json</span>.
          </p>
        </div>
        <button type="button" onClick={logout} className="btn-ghost">
          Log out
        </button>
      </section>

      {loading && (
        <div className="card text-sm text-ink-500">Loading…</div>
      )}

      {!loading && items && items.length === 0 && (
        <div className="card text-sm text-ink-500">No submissions yet.</div>
      )}

      {!loading &&
        items &&
        items.map((sub, idx) => {
          const open = openIdx === idx;
          return (
            <article key={idx} className="card">
              <button
                type="button"
                onClick={() => setOpenIdx(open ? null : idx)}
                className="flex w-full items-center justify-between gap-3 text-left"
              >
                <div>
                  <p className="text-sm font-semibold text-ink-900">
                    {sub.intervieweeName || "(no name)"}
                  </p>
                  <p className="text-xs text-ink-500">
                    Submitted {sub.submittedAt} ·{" "}
                    {Math.round((sub.durationSeconds ?? 0) / 60)} min
                  </p>
                </div>
                <span className="text-xs text-ink-500">
                  {open ? "▲ Collapse" : "▼ Expand"}
                </span>
              </button>
              {open && (
                <div className="mt-5 space-y-6">
                  {SECTIONS.map((section) => (
                    <div key={section.id}>
                      <h3 className="text-sm font-semibold text-ink-900">
                        {section.title}{" "}
                        <span className="text-xs font-normal text-ink-500">
                          ({section.titleKo})
                        </span>
                      </h3>
                      <dl className="mt-3 space-y-3">
                        {section.questions.map((q) => (
                          <div
                            key={q.id}
                            className="rounded-md border border-ink-200 bg-ink-50/40 p-3"
                          >
                            <dt className="text-xs font-semibold text-ink-700">
                              {q.number} · {q.prompt}
                            </dt>
                            <dd className="mt-1 whitespace-pre-wrap text-sm text-ink-900">
                              {formatValue(q, sub.answers?.[q.id])}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  ))}
                  <details className="rounded border border-ink-200 bg-ink-50/40 p-3">
                    <summary className="cursor-pointer text-xs text-ink-500">
                      Raw JSON
                    </summary>
                    <pre className="mt-3 overflow-x-auto text-xs">
                      {JSON.stringify(sub, null, 2)}
                    </pre>
                  </details>
                </div>
              )}
            </article>
          );
        })}

      <p className="text-xs text-ink-400">
        Tip: only {ALL_QUESTIONS.length} questions are defined; older
        submissions may have fewer answers if the form changed.
      </p>
    </div>
  );
}
