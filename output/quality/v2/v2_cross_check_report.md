# v2 ↔ raw MD cross-check 보고서

- 샘플 수: 10

## 컬럼
- match_kind: exact_code+pet (best) / contains+pet / base+pet / *(any_pet) (fallback)
- verbatim(contiguous): 원문발췌가 라인범위 내 연속 substring으로 발견되는가
- sentence-match: 원문발췌의 sentence 중 라인범위 내 substring 비율

| # | manual | spec code | spec petition | actual code | actual petition | match_kind | verbatim | sentence-match | 이슈 |
|---:|---|---|---|---|---|---|:---:|---:|---|
| 1 | stay | F-6 (F-6-1) | 체류자격 변경 | F-6 (F-6-1) | 체류자격 변경 | exact_code+pet | X | 49% | 낮은 sentence-match 49% — 라인범위와 본문 불일치 의심 |
| 2 | stay | E-7-4 | 체류자격 변경 | E-7 (E-7-4R) | 체류기간 연장 | contains(any_pet) | X | 100% | non-contiguous verbatim (sentence-match 100%); 신청종류 mismatch: spec='체류자격 변경', actual='체류기간 연장' (match_kind=contains(any_pet)) |
| 3 | visa | D-2 | 사증발급 | D-2 | 사증발급 | exact_code+pet | X | 76% | partial sentence-match 76% — 일부 sentence 가 라인범위에 없음 |
| 4 | visa | A-1 | 사증발급 | A-1 | 사증발급 | exact_code+pet | X | 100% | non-contiguous verbatim (sentence-match 100%) |
| 5 | stay | F-5 | 체류자격 변경 | F-5 (F-5-1) | 체류자격 변경 | contains+pet | X | 93% | non-contiguous verbatim (sentence-match 93%) |
| 6 | visa | C-3-3 | 사증발급 | G-1 (C-3-3) | 사증발급 | contains+pet | X | 100% | non-contiguous verbatim (sentence-match 100%) |
| 7 | visa | D-8 | 사증발급 | D-8 (D-8-1, D-8-2, D-8-3, D-8-4) | 사증발급 | contains+pet | X | 92% | non-contiguous verbatim (sentence-match 92%) |
| 8 | visa | E-9 | 사증발급 | E-9 (E-9-2) | 사증발급 | contains+pet | X | 58% | partial sentence-match 58% — 일부 sentence 가 라인범위에 없음 |
| 9 | stay | F-4 | 체류자격 부여 | F-4 | 거소신고 | exact_code(any_pet) | O | 100% | 신청종류 mismatch: spec='체류자격 부여', actual='거소신고' (match_kind=exact_code(any_pet)) |
| 10 | stay | H-2 | 체류기간 연장 | H-2 | 체류기간 연장 | exact_code+pet | X | 100% | non-contiguous verbatim (sentence-match 100%) |