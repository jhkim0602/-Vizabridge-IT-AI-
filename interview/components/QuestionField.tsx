"use client";

import type { Question } from "@/lib/types";

interface Props {
  question: Question;
  value: string | string[] | undefined;
  onChange: (next: string | string[]) => void;
}

export function QuestionField({ question, value, onChange }: Props) {
  return (
    <div className="space-y-1">
      <div className="flex items-baseline gap-2">
        <span className="chip">{question.number}</span>
        {question.optional && (
          <span className="text-xs text-ink-400">optional</span>
        )}
      </div>
      <label className="field-label">{question.prompt}</label>
      {question.promptKo && (
        <p className="text-xs text-ink-500">{question.promptKo}</p>
      )}
      {question.help && <p className="field-help">{question.help}</p>}
      {question.helpKo && (
        <p className="text-xs text-ink-400">{question.helpKo}</p>
      )}

      {question.type === "short" && (
        <input
          type="text"
          className="input-base"
          placeholder={question.placeholder}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
        />
      )}

      {question.type === "long" && (
        <textarea
          className="input-base min-h-[120px] resize-y"
          rows={5}
          placeholder={question.placeholder}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
        />
      )}

      {question.type === "single" && question.options && (
        <div className="mt-2 space-y-2">
          {question.options.map((opt) => {
            const checked = value === opt.value;
            return (
              <label
                key={opt.value}
                className={`flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 text-sm transition ${
                  checked
                    ? "border-brand-400 bg-brand-50/60 text-ink-900"
                    : "border-ink-200 bg-white text-ink-700 hover:bg-ink-50"
                }`}
              >
                <input
                  type="radio"
                  name={question.id}
                  className="mt-0.5 h-4 w-4 accent-brand-600"
                  checked={checked}
                  onChange={() => onChange(opt.value)}
                />
                <span>
                  <span className="font-medium">{opt.label}</span>
                  {opt.labelKo && (
                    <span className="ml-2 text-xs text-ink-500">
                      {opt.labelKo}
                    </span>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      )}

      {question.type === "multi" && question.options && (
        <div className="mt-2 space-y-2">
          {question.options.map((opt) => {
            const arr = Array.isArray(value) ? value : [];
            const checked = arr.includes(opt.value);
            return (
              <label
                key={opt.value}
                className={`flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 text-sm transition ${
                  checked
                    ? "border-brand-400 bg-brand-50/60 text-ink-900"
                    : "border-ink-200 bg-white text-ink-700 hover:bg-ink-50"
                }`}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 accent-brand-600"
                  checked={checked}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onChange([...arr, opt.value]);
                    } else {
                      onChange(arr.filter((v) => v !== opt.value));
                    }
                  }}
                />
                <span>
                  <span className="font-medium">{opt.label}</span>
                  {opt.labelKo && (
                    <span className="ml-2 text-xs text-ink-500">
                      {opt.labelKo}
                    </span>
                  )}
                </span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
