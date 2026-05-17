import Link from "next/link";
import { SECTIONS } from "@/lib/questions";

export default function LandingPage() {
  const totalQuestions = SECTIONS.reduce(
    (acc, s) => acc + s.questions.length,
    0,
  );

  return (
    <div className="space-y-10">
      <section className="card">
        <span className="chip">For Vizabridge interns · ~45 minutes</span>
        <h1 className="mt-4 text-2xl font-semibold tracking-tight text-ink-900 sm:text-3xl">
          Help us understand how you're building the Vizabridge AI chatbot.
        </h1>
        <p className="mt-3 text-sm leading-6 text-ink-600 sm:text-base">
          We're the data team behind Vizabridge — a preprocessing pipeline that
          turns Korean immigration manuals (체류민원 & 사증민원) into
          structured CSVs designed for chatbot use. This short interview has
          two goals:
        </p>
        <ul className="mt-4 grid gap-3 text-sm text-ink-700 sm:grid-cols-2">
          <li className="rounded-lg border border-ink-200 bg-ink-50/60 p-4">
            <p className="font-semibold text-ink-900">1 · Understand</p>
            <p className="mt-1 text-ink-600">
              How the three of you are building the chatbot today —
              architecture, data sources, what's stuck.
            </p>
          </li>
          <li className="rounded-lg border border-ink-200 bg-ink-50/60 p-4">
            <p className="font-semibold text-ink-900">2 · Share</p>
            <p className="mt-1 text-ink-600">
              What our pipeline produced, the chatbot-ready fields, and how to
              plug them in.
            </p>
          </li>
        </ul>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
          <Link href="/interview" className="btn-primary">
            Start the interview →
          </Link>
          <p className="text-xs text-ink-500">
            {SECTIONS.length} sections · {totalQuestions} questions · your
            draft is auto-saved in your browser.
          </p>
        </div>
      </section>

      <section className="card">
        <h2 className="text-lg font-semibold tracking-tight text-ink-900">
          What we'll cover
        </h2>
        <ol className="mt-4 divide-y divide-ink-200">
          {SECTIONS.map((section, idx) => (
            <li
              key={section.id}
              className="flex items-start gap-4 py-4 first:pt-0 last:pb-0"
            >
              <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700">
                {idx + 1}
              </span>
              <div className="flex-1">
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <p className="text-sm font-semibold text-ink-900">
                    {section.title}
                  </p>
                  <p className="text-xs text-ink-500">
                    {section.titleKo} · {section.duration}
                  </p>
                </div>
                {section.intro && (
                  <p className="mt-1 text-sm text-ink-600">{section.intro}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="card">
        <h2 className="text-lg font-semibold tracking-tight text-ink-900">
          Privacy
        </h2>
        <p className="mt-2 text-sm text-ink-600">
          This site does not have a backend database. Your answers are kept in
          your browser as you go. When you finish, you'll be shown a summary
          and given the option to download a JSON file, copy your answers, or
          send them by email. Nothing is uploaded anywhere automatically.
        </p>
      </section>
    </div>
  );
}
