export function DataBriefing() {
  return (
    <article className="space-y-6 text-sm leading-6 text-ink-700">
      <header>
        <span className="chip">Data briefing · 3 minutes read</span>
        <h2 className="mt-3 text-lg font-semibold text-ink-900">
          What our preprocessing pipeline produced
        </h2>
        <p className="mt-1 text-xs text-ink-500">
          파이프라인이 만든 결과물과, 그것을 어떻게 쓰면 좋을지에 대한 요약
          브리핑입니다.
        </p>
      </header>

      <section>
        <h3 className="text-sm font-semibold text-ink-900">Two tiers of CSV</h3>
        <p className="mt-1 text-xs text-ink-500">
          체류민원(장기 체류 허가)과 사증민원(비자 발급) 각각에 대해 두 가지
          버전의 CSV가 있습니다.
        </p>
        <div className="mt-3 overflow-x-auto rounded-md border border-ink-200">
          <table className="w-full table-fixed text-left text-xs">
            <thead className="bg-ink-50 text-ink-700">
              <tr>
                <th className="w-1/2 px-3 py-2 font-semibold">CSV</th>
                <th className="px-3 py-2 font-semibold">Purpose</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-200">
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  stay_manual_semantic_clean.csv
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Administrative structure preserved: code + petition type +
                  subsection (requirements, documents, fees, quotas,
                  restrictions, exceptions).
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  visa_manual_semantic_clean.csv
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Same structure, for the visa issuance side.
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  stay_manual_chatbot_ready.csv
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Adds user-facing fields: situation tags, natural-language
                  keywords, follow-up questions, routing hints.
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  visa_manual_chatbot_ready.csv
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Same structure, for visa issuance.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-ink-900">Scale</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-700">
          <li>
            <strong>Stay Permit Manual:</strong> 34 source chunks → 181 unique
            stay status codes (D-2, E-7, F-2-R, F-5-27 …).
          </li>
          <li>
            <strong>Visa Manual:</strong> 23 source chunks → 159 unique visa
            codes (C-3, D-8, E-7, F-6 …).
          </li>
          <li>
            Validation passed with <strong>0 issues</strong> on both manuals —
            data integrity confirmed.
          </li>
        </ul>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-ink-900">
          Key chatbot-ready fields
        </h3>
        <p className="mt-1 text-xs text-ink-500">
          사용자가 비자 코드를 모르더라도 자연어로 검색할 수 있게 해주는 핵심
          필드입니다.
        </p>
        <div className="mt-3 overflow-x-auto rounded-md border border-ink-200">
          <table className="w-full table-fixed text-left text-xs">
            <thead className="bg-ink-50 text-ink-700">
              <tr>
                <th className="w-2/5 px-3 py-2 font-semibold">Field</th>
                <th className="px-3 py-2 font-semibold">What it gives the chatbot</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-200">
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  situation_tags
                </td>
                <td className="px-3 py-2 text-ink-700">
                  21 situation categories (marriage/spouse, study/training,
                  employment, investment/startup …) — maps user natural
                  language to these tags.
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  natural_language_keywords
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Natural-language search terms users actually type.
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  plain_language_summary
                </td>
                <td className="px-3 py-2 text-ink-700">
                  One-sentence human-readable summary of a rule.
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  required_user_info
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Questions the chatbot should ask before answering (current
                  visa status, employer type, etc.).
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  routing_hint
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Directs to stay permit vs. visa issuance channel.
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  emphasis
                </td>
                <td className="px-3 py-2 text-ink-700">
                  What aspect to emphasize (documents, restrictions, scoring
                  table, quota).
                </td>
              </tr>
              <tr>
                <td className="px-3 py-2 font-mono text-[11px] text-ink-800">
                  search_text
                </td>
                <td className="px-3 py-2 text-ink-700">
                  Pre-built combined text ready for vector indexing.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-ink-900">
          Structural insight: codes are not the entry point
        </h3>
        <p className="mt-1 text-ink-700">
          The manuals are organized by code (A-1, D-2, E-7 …), but users never
          start with a code. The chatbot-ready CSV bridges this gap by
          indexing via situation tags and intent keywords rather than codes.
        </p>
        <div className="mt-3 rounded-md border border-brand-200 bg-brand-50/50 p-3 text-xs text-brand-900">
          <p className="font-semibold">Recommended chatbot flow</p>
          <p className="mt-1 font-mono leading-5">
            User utterance
            <br />
            &nbsp;&nbsp;→ Intent classification (situation_tags)
            <br />
            &nbsp;&nbsp;→ Routing hint (stay permit vs. visa, petition type)
            <br />
            &nbsp;&nbsp;→ Vector search on search_text
            <br />
            &nbsp;&nbsp;→ Retrieve row(s) → Answer using
            plain_language_summary + required_user_info
          </p>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-semibold text-ink-900">
          What the data does NOT contain
        </h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-700">
          <li>Page numbers or raw OCR text (stripped by design).</li>
          <li>
            Legal interpretation — only what is written in the official
            manual.
          </li>
          <li>
            Real-time quota availability (quotas change; the CSV captures the
            rule, not live numbers).
          </li>
        </ul>
      </section>
    </article>
  );
}
