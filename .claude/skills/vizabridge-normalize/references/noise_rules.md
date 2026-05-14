# Noise Rules

Drop the following from the source. Do not emit rows for them.

## Whole-chunk drops

If a chunk's content is essentially one of the following, emit an empty chunk block (markers only, no rows):

- Cover page (title + date + 법무부 / 출입국·외국인정책본부, nothing else)
- Table of contents (`目 次` table with code references but no rules)
- Pure heading lists with no body (e.g. a numbered topic list)

## Row-level drops

Do not emit a row when the source content is:

- **Blank attachment / form titles** with no body. Common offenders:
  - 확인서
  - 계획서
  - 카드(예시)
  - 신상 기술서
  - signature/seal
  - 검 사 내 용

- **Bilingual form scaffolds** that are themselves not rules. Common offenders:
  - ROWSPANCONTINUE
  - 근로계약서 견본 / Labor Contract(Sample)
  - Employment Permit
  - Payment methods

- **Short table fragment titles** that escaped a parent table:
  - `구분`, `구 분`, `내용`, `일반`, `일반식당`, `소득`, `쿼터`

  These are leftover header cells. If a "row" is just one of those words plus whitespace, skip.

- **Pure page-decoration text**: page numbers, repeated 보 안 검 인, watermarks. kordoc usually strips these, but if any survive, drop them.

## Heuristic checks

When unsure whether a candidate row is signal or noise, ask:

1. Does this text answer a specific question (who can apply, what documents are needed, what's the fee)? → keep
2. Does it just label a section without content? → drop
3. Is it a multilingual translation of a Korean form template? → drop
4. Is it a 유의사항 / 공통사항 that applies broadly? → keep as `item_type = common_rule` row with `petition_type = 공통사항`

## Forms appendix at the end

Many manuals tail-end into appendix forms (서약서, 신청서 양식, 확인서). These typically appear after the last regular visa-code section. Default rule: **drop**, unless the form itself contains substantive rules (e.g. F-4 비취업 서약서 has 제한 직업 목록 — keep the 직업 목록 as a row with `subsection_type = 제한`).

## Important: drop is silent

Do not emit notes like "(noise — skipped)" anywhere in the normalized file. The block markers themselves are the record that the chunk was processed. The downstream parser only reads `### row` blocks; everything else is invisible to it.
