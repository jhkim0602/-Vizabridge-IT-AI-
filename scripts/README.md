# Scripts

반복 실행이 필요한 정제 및 CSV 생성 코드를 이 폴더에 둡니다.

## 최종 CSV 생성

`data/parsed/`의 LlamaParse Markdown을 읽어 PDF당 최종 semantic CSV 하나씩 생성합니다.

```bash
.venv/bin/python scripts/build_semantic_manual_csvs.py
```

산출물:

- `data/processed/stay_manual_semantic_clean.csv`
- `data/processed/visa_manual_semantic_clean.csv`

최종 CSV에는 PDF 페이지 번호, 원문 근거, raw text, review/debug 컬럼을 포함하지 않습니다.
