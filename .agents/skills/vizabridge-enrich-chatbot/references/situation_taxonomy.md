# Situation Taxonomy

Pick one or more `user_situation_tags` per row from this canonical list. Choose all that genuinely apply; do not stretch to fit categories that don't.

## Top-level tags

| Tag | When to use |
| --- | --- |
| `결혼/배우자` | F-6 결혼이민, F-1 방문동거 (한국인 배우자), F-2 일부, 동반가족 사항 |
| `유학/연수` | D-2 유학, D-4 일반연수, D-3 기술연수 |
| `취업/고용` | E-1~E-7 직업 비자, E-9 비전문취업, E-10 선원취업, H-2 방문취업, 단기취업(C-4) |
| `창업/투자` | D-8 기업투자, D-9 무역경영, K-STAR / 스타트업 트랙, F-5 영주 중 투자 트랙 |
| `구직` | D-10 구직, 졸업 후 취업 활동 |
| `방문/단기체류` | B-1 사증면제, B-2 관광통과, C-3 단기방문, C-1 일시취재 |
| `가족초청/동반` | F-1 방문동거, F-3 동반, 미성년 자녀 / 부모 초청 |
| `재외동포` | F-4, H-2 동포 |
| `영주신청` | F-5 영주 |
| `자격변경` | 체류자격 변경허가 전반 |
| `기간연장` | 체류기간 연장허가 전반 |
| `근무처변경` | 근무처 변경 / 추가 |
| `자격외활동` | 체류자격외 활동허가 (유학생 아르바이트 등) |
| `재입국` | 재입국허가 |
| `외국인등록` | 외국인등록증 신규/변경 |
| `공무/외교` | A-1 외교, A-2 공무, A-3 협정 |
| `종교/문화` | D-1 문화예술, D-6 종교 |
| `숙련기능` | E-7-4 숙련기능인력 (점수제) |
| `계절근로` | E-8 계절근로 |
| `지역특화` | F-2-R 지역특화형 우수인재 |
| `우수인재` | F-2 우수인재, 탑티어 비자 (D-10-T, E-7-T, F-2-T, F-5-T) |
| `난민/인도적체류` | G-1 기타 (난민, 인도적체류) |
| `결핵검진` | 공통사항 결핵진단서 제출 의무 |
| `공통사항` | 매뉴얼 공통 안내, 유의사항 |

## Combination rules

- A row often has 2-3 tags. E.g. F-2-R has `[지역특화, 우수인재, 자격변경]`.
- Don't tag with `자격변경` / `기간연장` etc. unless the row's `petition_type` actually corresponds. The petition_type is the source of truth.
- `공통사항` is mutually exclusive with code-specific tags. If the row is a common rule (결핵, 공통서류 등), use `공통사항` alone or with `결핵검진`-class subtags.

## Examples

- D-8 사증발급 / 요건 → `[창업/투자]`
- F-6 사증발급 / 대상 → `[결혼/배우자]`
- F-6 체류자격 변경 / 제출서류 → `[결혼/배우자, 자격변경]`
- D-2 체류자격외 활동허가 / 절차 → `[유학/연수, 자격외활동]`
- E-7-4 체류자격 변경 / 점수표 → `[숙련기능, 취업/고용, 자격변경]`
- F-4 사증발급 / 대상 → `[재외동포]`
- G-1-99 체류자격 변경 / 요건 → `[난민/인도적체류, 자격변경]`
- 공통사항 / 결핵진단서 / 제출서류 → `[공통사항, 결핵검진]`
