# Keyword Rules

`intent_keywords` is the most important chatbot field — it bridges what a user actually types and what the semantic row contains.

## Composition

For each row, emit 3-7 short Korean phrases that a user might enter while looking for this row's content. Mix:

1. **Situation-language phrases** — the user describes themselves. "한국인 배우자와 결혼했어요", "유학생인데 아르바이트 가능한가요", "외국인 직원 채용하고 싶어요".
2. **Question-style phrases** — the user asks. "F-6 비자 받으려면 어떻게 해야 하나요", "기업투자 비자 제출서류".
3. **Plain noun phrases** — partial matches for short queries. "결혼이민 자격변경", "투자 비자 1억원".

Avoid pure code-mention phrases ("D-8") — those are already in `primary_code` and `search_text`. The keyword field is for natural language.

## Length & form

- Each phrase: 8-30 Korean characters. Whole sentences are fine but not required.
- Output as a bullet list under a `|` literal block.
- No code formatting, no quotes inside individual phrases (puts them in normalized text fine but adds visual noise).
- Avoid duplicating phrases that differ only by stop-word ("어떻게 받나요" vs "어떻게 받습니까") — pick one.

## Rules of restraint

- **Do not invent facts.** Phrases must refer to circumstances that the semantic row actually addresses. A row about D-2 sub-codes is not addressed by "한국 영주권 신청".
- **Match the row's petition_type.** A row about `체류기간 연장` should phrase around "기간 연장하고 싶어요", not "처음 신청합니다".
- **Mirror the semantic row's vocabulary.** If the row mentions `자격증` or `소득 2,500만원`, those terms are good keywords. If it doesn't, don't add them.
- **One row's keywords ≠ another's.** Two rows about the same visa code but different subsection_types should have distinct keywords (one about documents, another about restrictions).

## Anti-patterns

- "비자 신청하고 싶어요" — too generic, applies to anything
- "출입국관리법 제○○조" — legal jargon users don't type
- "D-8 사증발급인정서 신청 서류 첨부 안내" — basically the section title; not user language
- Single English words ("visa", "employment") — Korean users mix English but full English phrases miss

## Example: D-8 기업투자 / 사증발급 / 요건

```
- intent_keywords: |
    - 한국에서 법인을 설립하고 싶다
    - 외국인 투자비자
    - 1억원 이상 투자하면 비자 받나요
    - 외국인 한국 사업 시작
    - 기업투자 비자 자격요건
```

## Example: E-7-4 체류자격 변경 / 요건

```
- intent_keywords: |
    - 숙련기능 점수제 신청
    - E-9에서 E-7-4로 자격변경
    - 비전문취업 4년 일했어요
    - 외국인 근로자 자격변경
    - 농촌 비수도권 근무하고 싶다
    - 한국어 시험 점수 부족해도 되나
```

## Example: 공통사항 / 결핵진단서 / 제출서류

```
- intent_keywords: |
    - 결핵 진단서 어디서 받나요
    - 베트남에서 한국 장기 비자 신청
    - 결핵 고위험국가 비자
    - 사증 신청 결핵검사
```
